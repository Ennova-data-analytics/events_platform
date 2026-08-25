import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from domain import schemas, models
from domain.use_cases.db_recruitment import RecruitmentUseCases
from domain.use_cases.db_applications import HrApplicationUseCases, compute_funnel
from api import deps

router = APIRouter()


def _actor(user: models.User) -> str:
    return user.full_name or user.email


def _ensure_can_manage_department(db: Session, user: models.User, department_id: int) -> None:
    """Super-admins manage any department; recruiters only their scoped ones."""
    if deps.is_super_admin(user):
        return
    scoped = RecruitmentUseCases.get_recruiter_departments(db, user.user_id)
    if department_id not in scoped:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this department",
        )


# ── Departments ─────────────────────────────────────────────────────────────
@router.get("/departments", response_model=List[schemas.Department])
def list_departments(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_recruiter),
):
    """All departments for super-admins; only the recruiter's scoped departments otherwise."""
    departments = RecruitmentUseCases.list_departments(db)
    scoped = deps.recruiter_department_ids(db, current_user)
    if scoped is None:
        return departments
    return [d for d in departments if d.department_id in scoped]


@router.post("/departments", response_model=schemas.Department, status_code=status.HTTP_201_CREATED)
def create_department(
    data: schemas.DepartmentCreate,
    db: Session = Depends(deps.get_db),
    current_admin: models.User = Depends(deps.get_current_active_admin),
):
    return RecruitmentUseCases.create_department(db, data)


@router.patch("/departments/{department_id}", response_model=schemas.Department)
def update_department(
    department_id: int,
    data: schemas.DepartmentUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_recruiter),
):
    _ensure_can_manage_department(db, current_user, department_id)
    return RecruitmentUseCases.update_department(db, department_id, data)


@router.put("/departments/{department_id}/calendly", response_model=schemas.Department)
def set_department_calendly(
    department_id: int,
    data: schemas.DepartmentCalendlyUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_recruiter),
):
    _ensure_can_manage_department(db, current_user, department_id)
    return RecruitmentUseCases.set_department_calendly(db, department_id, data.calendly_link)


@router.put("/departments/{department_id}/criteria", response_model=schemas.Department)
def set_department_criteria(
    department_id: int,
    data: schemas.DepartmentCriteriaUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_recruiter),
):
    _ensure_can_manage_department(db, current_user, department_id)
    return RecruitmentUseCases.set_department_criteria(db, department_id, data.scoring_criteria)


@router.put("/departments/{department_id}/questions", response_model=schemas.Department)
def set_department_questions(
    department_id: int,
    data: schemas.DepartmentQuestionsUpdate,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_recruiter),
):
    _ensure_can_manage_department(db, current_user, department_id)
    return RecruitmentUseCases.set_department_questions(db, department_id, data.custom_questions)


# ── Cohorts (recruitment cycles) — setup is super-admin only ────────────────
@router.get("/cycles", response_model=List[schemas.RecruitmentCycle])
def list_cycles(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_recruiter),
):
    return RecruitmentUseCases.list_cycles(db)


@router.get("/cycles/{cycle_id}", response_model=schemas.RecruitmentCycle)
def get_cycle(
    cycle_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_recruiter),
):
    return RecruitmentUseCases.get_cycle(db, cycle_id)


@router.post("/cycles", response_model=schemas.RecruitmentCycle, status_code=status.HTTP_201_CREATED)
def create_cycle(
    data: schemas.RecruitmentCycleCreate,
    db: Session = Depends(deps.get_db),
    current_admin: models.User = Depends(deps.get_current_active_admin),
):
    return RecruitmentUseCases.create_cycle(db, data, created_by_user_id=current_admin.user_id)


@router.patch("/cycles/{cycle_id}", response_model=schemas.RecruitmentCycle)
def update_cycle(
    cycle_id: int,
    data: schemas.RecruitmentCycleUpdate,
    db: Session = Depends(deps.get_db),
    current_admin: models.User = Depends(deps.get_current_active_admin),
):
    return RecruitmentUseCases.update_cycle(db, cycle_id, data)


@router.post("/cycles/{cycle_id}/activate", response_model=schemas.RecruitmentCycle)
def activate_cycle(
    cycle_id: int,
    db: Session = Depends(deps.get_db),
    current_admin: models.User = Depends(deps.get_current_active_admin),
):
    return RecruitmentUseCases.activate_cycle(db, cycle_id)


@router.delete("/cycles/{cycle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cycle(
    cycle_id: int,
    db: Session = Depends(deps.get_db),
    current_admin: models.User = Depends(deps.get_current_active_admin),
):
    RecruitmentUseCases.delete_cycle(db, cycle_id)


# ── Recruiter → department assignment (super-admin only) ────────────────────
@router.get("/recruiters/{user_id}/departments", response_model=List[int])
def get_recruiter_departments(
    user_id: uuid.UUID,
    db: Session = Depends(deps.get_db),
    current_admin: models.User = Depends(deps.get_current_active_admin),
):
    return RecruitmentUseCases.get_recruiter_departments(db, user_id)


@router.put("/recruiters/{user_id}/departments", response_model=List[int])
def set_recruiter_departments(
    user_id: uuid.UUID,
    data: schemas.RecruiterDepartmentsUpdate,
    db: Session = Depends(deps.get_db),
    current_admin: models.User = Depends(deps.get_current_active_admin),
):
    return RecruitmentUseCases.set_recruiter_departments(db, user_id, data.department_ids)


# ── Applications (recruiter panel, department-scoped) ───────────────────────
@router.get("/applications")
def list_applications(
    cycle_id: int | None = Query(None),
    department_id: int | None = Query(None),
    stage: str | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_recruiter),
):
    scoped = deps.recruiter_department_ids(db, current_user)
    return HrApplicationUseCases.list_applications(
        db, scoped, cycle_id=cycle_id, department_id=department_id, stage=stage, search=search)


@router.get("/applications/{application_id}")
def get_application(
    application_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_recruiter),
):
    scoped = deps.recruiter_department_ids(db, current_user)
    return HrApplicationUseCases.get_application(db, scoped, application_id)


@router.patch("/applications/{application_id}/status")
def change_status(
    application_id: int,
    data: schemas.StatusChangeIn,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_recruiter),
):
    scoped = deps.recruiter_department_ids(db, current_user)
    return HrApplicationUseCases.change_status(db, scoped, application_id, data.status, _actor(current_user))


@router.patch("/applications/{application_id}/department")
def set_final_department(
    application_id: int,
    data: schemas.FinalDepartmentIn,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_recruiter),
):
    scoped = deps.recruiter_department_ids(db, current_user)
    return HrApplicationUseCases.set_final_department(db, scoped, application_id, data.department_id, _actor(current_user))


@router.post("/applications/{application_id}/notes")
def add_note(
    application_id: int,
    data: schemas.NoteIn,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_recruiter),
):
    scoped = deps.recruiter_department_ids(db, current_user)
    return HrApplicationUseCases.add_note(db, scoped, application_id, data.text, _actor(current_user))


@router.get("/applications/{application_id}/cv")
def get_cv_url(
    application_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_recruiter),
):
    scoped = deps.recruiter_department_ids(db, current_user)
    return HrApplicationUseCases.cv_url(db, scoped, application_id)


@router.post("/applications/{application_id}/send-interview-invite")
def send_interview_invite(
    application_id: int,
    data: schemas.InterviewInviteIn,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_recruiter),
):
    scoped = deps.recruiter_department_ids(db, current_user)
    return HrApplicationUseCases.send_interview_invite(db, scoped, application_id, data.calendly_link or "", _actor(current_user))


@router.post("/applications/{application_id}/send-case")
def send_case(
    application_id: int,
    data: schemas.CaseSendIn,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_recruiter),
):
    scoped = deps.recruiter_department_ids(db, current_user)
    return HrApplicationUseCases.send_marketing_case(db, scoped, application_id, data.brief_url, data.hours, _actor(current_user))


@router.get("/analytics/funnel")
def analytics_funnel(
    cycle_id: int = Query(...),
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_recruiter),
):
    scoped = deps.recruiter_department_ids(db, current_user)
    return compute_funnel(db, cycle_id, scoped)
