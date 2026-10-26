from typing import Literal

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from quiz_engine import quiz_service
from quiz_llm import QuizModelUnavailable

router = APIRouter(prefix='/quiz', tags=['Dinámica de primaria'])


class StartRequest(BaseModel):
    grade: int = Field(ge=1, le=6)
    subject: Literal['mixto', 'matematicas', 'ciencias_naturales', 'geografia', 'biologia', 'espanol'] = 'mixto'


class SessionRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=40)


class QuestionRequest(SessionRequest):
    question_id: str = Field(min_length=1, max_length=40)


class AnswerRequest(QuestionRequest):
    answer: str = Field(min_length=1, max_length=2000)


def speak(text):
    from tts_engine import tts_service
    return tts_service.synthesize_to_base64_wav(text)


def respond(action, *args):
    try:
        result = action(*args)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except QuizModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    audio = result.pop('_prepared_audio', None)
    result['audio'] = audio or speak(result['response'])
    return result


@router.post('/prepare')
def prepare(request: StartRequest):
    return quiz_service.prepare(request.grade, request.subject)


@router.get('/prepare')
def preparation_status(request: StartRequest = Depends()):
    return quiz_service.generator.status(request.grade, request.subject)


@router.get('/fillers')
def fillers():
    get = getattr(quiz_service.generator, 'fillers', None)
    return {'fillers': get() if get else []}


@router.post('/start')
def start(request: StartRequest):
    return respond(quiz_service.start, request.grade, request.subject)


@router.post('/answer')
def answer(request: AnswerRequest):
    return respond(quiz_service.answer, request.session_id, request.question_id, request.answer)


@router.post('/next')
def next_question(request: QuestionRequest):
    return respond(quiz_service.next, request.session_id, request.question_id)


@router.post('/end')
def end(request: SessionRequest):
    quiz_service.end(request.session_id)
    return {'status': 'ok'}
