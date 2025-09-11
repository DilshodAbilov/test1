import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum

from tests.models import (
    User as AppUser,
    Group,
    Questions,
    Answer,
    UserAnswers,
    GroupUsers,
    Result,
)

class TestConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_question_task = None
        self.current_question_start_time = {}

    async def connect(self):
        self.room_code = self.scope["url_route"]["kwargs"]["room_code"]
        self.room_group_name = f"test_{self.room_code}"

        auth_user = self.scope.get("user", None)
        self.app_user = await self._map_to_app_user(auth_user)
        if not self.app_user:
            await self.close(code=4401)
            return

        self.group_obj = await self._ensure_membership(self.room_code, self.app_user.id)
        self.role = "admin" if self.app_user.is_admin else "student"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "system_message", "payload": {"message": f"{self.app_user.username} ({self.role}) qo'shildi"}}
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        if getattr(self, "app_user", None):
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "system_message", "payload": {"message": f"{self.app_user.username} chiqib ketdi"}})
        if self.current_question_task:
            self.current_question_task.cancel()

    async def receive(self, text_data):
        try:
            data = json.loads(text_data or "{}")
            action = data.get("action")
            if not action:
                return await self._send_error("Action yo‘q")

            if action == "start_test":
                if not self._is_admin():
                    return await self._send_error("Ruxsat yo‘q (admin kerak).")
                await self._start_test()
                return

            if action == "next_question":
                if not self._is_admin():
                    return await self._send_error("Ruxsat yo‘q (admin kerak).")
                question_id = data.get("question_id")
                if not question_id:
                    return await self._send_error("question_id kerak.")
                if self.current_question_task:
                    self.current_question_task.cancel()
                self.current_question_start_time = {}
                await self._broadcast_question(question_id)
                return

            if action == "finish_test":
                if not self._is_admin():
                    return await self._send_error("Ruxsat yo‘q (admin kerak).")
                await self._finish_test()
                return

            if action == "submit_answer":
                if self._is_admin():
                    return await self._send_error("Admin javob yubora olmaydi.")
                question_id = data.get("question_id")
                answer_id = data.get("answer_id")
                if not question_id or not answer_id:
                    return await self._send_error("question_id va answer_id kerak.")
                await self._handle_submit_answer(question_id, answer_id)
                return

            return await self._send_error("Noma'lum action.")

        except Exception as e:
            return await self._send_error(str(e))

    async def _start_test(self):
        await self._mark_group_started(self.group_obj.id)
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "test_started", "payload": {"message": "Test boshlandi!", "group_id": self.group_obj.id}},
        )
        if self._is_admin():
            group_users = await self._get_all_group_users(self.group_obj.id)
            await self._send_json({"type": "admin_view", "students": group_users})

        await self._broadcast_question(0)

    async def _broadcast_question(self, question_id: int):
        if question_id == 0:
            q = await self._get_first_question(self.group_obj.id)
        else:
            q = await self._get_next_question(question_id, self.group_obj.id)

        if not q:
            await self._finish_test()
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "send_question", "payload": {"question": q}},
        )

        group_users = await self._get_all_group_users(self.group_obj.id)
        now = timezone.now()
        for u in group_users:
            self.current_question_start_time[u["id"]] = now

        if self.current_question_task:
            self.current_question_task.cancel()

        group_time = getattr(self.group_obj, "time", 10) or 10

        async def wait_and_continue():
            await asyncio.sleep(group_time)

            unanswered = await self._get_unanswered_users(q["id"], self.group_obj.id)
            for user in unanswered:
                await self._save_zero_for_user(q["id"], user["id"])

            next_q = await self._get_next_question(q["id"], self.group_obj.id)
            if next_q:
                self.current_question_start_time = {}
                await self._broadcast_question(next_q["id"])
            else:
                await self._finish_test()

        self.current_question_task = asyncio.create_task(wait_and_continue())

    async def _handle_submit_answer(self, question_id: int, answer_id: int):
        group = await self._get_group_obj(self.group_obj.id)
        if not group.is_active:
            return await self._send_error("Test tugagan, javob yuborolmaysiz.")

        save_info = await self._check_answer_and_save_safe(question_id, answer_id, self.app_user.id)
        if save_info is None:
            return await self._send_error("Question yoki Answer topilmadi.")
        if isinstance(save_info, dict):
            return await self._send_json({"type": "error", "error": save_info.get("detail")})

        score, is_correct = save_info
        await self._send_json({
            "type": "answer_feedback",
            "question_id": question_id,
            "is_correct": is_correct,
            "score": score,
            "message": "To‘g‘ri ✅" if is_correct else "Xato ❌"
        })

        leaderboard = await self._get_leaderboard(self.group_obj.id)
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "student_answer",
             "payload": {"user": self.app_user.username, "question_id": question_id, "score": score,
                         "is_correct": is_correct, "leaderboard": leaderboard}},
        )

    async def _finish_test(self):
        await self._mark_group_finished(self.group_obj.id)
        group_results = await self._mark_group_finished_and_collect_results(self.group_obj.id)
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "final_results", "results": group_results},
        )
        if self.current_question_task:
            self.current_question_task.cancel()
        self.current_question_start_time = {}

    async def system_message(self, event):
        await self._send_json({"type": "message", **event["payload"]})

    async def test_started(self, event):
        await self._send_json({"type": "test_started", **event["payload"]})

    async def send_question(self, event):
        await self._send_json({"type": "question", **event["payload"]})

    async def student_answer(self, event):
        if self._is_admin():
            await self._send_json({"type": "student_answer", **event["payload"]})

    async def final_results(self, event):
        await self._send_json({"type": "final_results", "results": event["results"]})

    async def test_finished_event(self, event):
        await self._send_json({"type": "test_finished", **event["payload"]})

    async def _send_error(self, message: str):
        await self.send(text_data=json.dumps({"type": "error", "error": message}))

    async def _send_json(self, payload: dict):
        await self.send(text_data=json.dumps(payload))

    def _is_admin(self) -> bool:
        return bool(self.app_user and self.app_user.is_admin)

    @database_sync_to_async
    def _map_to_app_user(self, auth_user):
        if not auth_user or not getattr(auth_user, "is_authenticated", False):
            return None
        username = getattr(auth_user, "username", None)
        if not username:
            return None
        app_user, _ = AppUser.objects.get_or_create(
            username=username,
            defaults={"is_admin": getattr(auth_user, "is_staff", False)},
        )
        return app_user

    @database_sync_to_async
    def _ensure_membership(self, room_code: str, user_id: int):
        group = Group.objects.get(code=room_code)
        GroupUsers.objects.get_or_create(group=group, user_id=user_id)
        return group

    @database_sync_to_async
    def _mark_group_started(self, group_id: int):
        Group.objects.filter(id=group_id).update(is_active=True, start_time=timezone.now())

    @database_sync_to_async
    def _mark_group_finished(self, group_id: int):
        Group.objects.filter(id=group_id).update(is_active=False)

    @database_sync_to_async
    def _mark_group_finished_and_collect_results(self, group_id: int):
        qs = (UserAnswers.objects
              .filter(question__group=group_id)
              .values('user_id', 'user__username')
              .annotate(score=Sum('score'))
              .order_by('-score'))
        with transaction.atomic():
            Result.objects.filter(group_id=group_id).delete()
            for idx, r in enumerate(qs, start=1):
                Result.objects.create(group_id=group_id, user_id=r["user_id"], score=r["score"] or 0, rank=idx)
        return list(qs)

    @database_sync_to_async
    def _get_all_group_users(self, group_id: int):
        users = GroupUsers.objects.filter(group_id=group_id).select_related("user")
        return [{"username": u.user.username, "id": u.user.id} for u in users]

    @database_sync_to_async
    def _get_group_obj(self, group_id: int):
        return Group.objects.get(id=group_id)

    @database_sync_to_async
    def _get_first_question(self, group_id: int):
        question = Questions.objects.filter(group=group_id).order_by("id").first()
        if question:
            answers = [{"id": a.id, "text": a.answer} for a in Answer.objects.filter(question=question.id)]
            return {"id": question.id, "text": question.question, "answers": answers}
        return None

    @database_sync_to_async
    def _get_next_question(self, current_question_id, group_id):
        q = Questions.objects.filter(id__gt=current_question_id, group=group_id).order_by("id").first()
        if q:
            answers = [{"id": a.id, "text": a.answer} for a in Answer.objects.filter(question=q.id)]
            return {"id": q.id, "text": q.question, "answers": answers}
        return None

    @database_sync_to_async
    def _check_answer_and_save_safe(self, question_id: int, answer_id: int, user_id: int):
        try:
            with transaction.atomic():
                question = Questions.objects.get(id=question_id)
                answer = Answer.objects.get(id=answer_id, question_id=question.id)

                existing_answer = UserAnswers.objects.filter(user_id=user_id, question_id=question.id).first()
                if existing_answer:
                    return {"detail": "Siz allaqachon javob bergansiz."}

                start_time = self.current_question_start_time.get(user_id)
                if not start_time:

                    start_time = timezone.now()


                level_score_map = {'LOW': 5, 'MEDIUM': 10, 'HIGH': 15}
                base_score = level_score_map.get(question.level, 5)

                group_time = getattr(self.group_obj, "time", 10) or 10

                time_taken = (timezone.now() - start_time).total_seconds()

                if answer.is_correct:
                    if time_taken >= group_time:
                        score = 0
                    else:
                        score = base_score * (1 - time_taken / group_time)
                        score = round(score, 2)
                else:
                    score = 0

                UserAnswers.objects.create(
                    user_id=user_id,
                    question=question,
                    answer=answer,
                    is_correct=answer.is_correct,
                    score=score
                )

                return (score, answer.is_correct)

        except (Questions.DoesNotExist, Answer.DoesNotExist):
            return None

    @database_sync_to_async
    def _save_zero_for_user(self, question_id, user_id):
        if not UserAnswers.objects.filter(question_id=question_id, user_id=user_id).exists():
            UserAnswers.objects.create(
                user_id=user_id,
                question_id=question_id,
                answer=None,
                is_correct=False,
                score=0
            )

    @database_sync_to_async
    def _get_user_result(self, user_id: int, group_id: int):
        res = UserAnswers.objects.filter(user_id=user_id, question__group=group_id).aggregate(score=Sum('score'))
        return {"score": res['score'] or 0}

    @database_sync_to_async
    def _get_leaderboard(self, group_id: int):
        qs = (UserAnswers.objects
              .filter(question__group=group_id)
              .values('user__username')
              .annotate(score=Sum('score'))
              .order_by('-score'))
        return list(qs)

    @database_sync_to_async
    def _get_unanswered_users(self, question_id, group_id):
        answered_ids = UserAnswers.objects.filter(question_id=question_id).values_list('user_id', flat=True)
        users = GroupUsers.objects.filter(group_id=group_id).exclude(user_id__in=answered_ids)
        return [{"id": u.user.id, "username": u.user.username} for u in users]
