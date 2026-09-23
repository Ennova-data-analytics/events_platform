from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from domain import models, schemas


class RecruitmentUseCases:
    """Phase 1: department catalog, cohorts (cycles) and recruiter scoping."""

    # ── Departments ─────────────────────────────────────────────────────────
    @staticmethod
    def list_departments(db: Session, active_only: bool = False) -> list[models.Department]:
        q = db.query(models.Department)
        if active_only:
            q = q.filter(models.Department.is_active.is_(True))
        return q.order_by(models.Department.name).all()

    @staticmethod
    def get_department(db: Session, department_id: int) -> models.Department:
        dep = db.query(models.Department).filter(models.Department.department_id == department_id).first()
        if not dep:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
        return dep

    @staticmethod
    def create_department(db: Session, data: schemas.DepartmentCreate) -> models.Department:
        payload = data.model_dump()
        # Pydantic sub-models (criteria/questions) need to be plain dicts for JSONB.
        dep = models.Department(**_jsonable(payload))
        db.add(dep)
        db.commit()
        db.refresh(dep)
        return dep

    @staticmethod
    def update_department(db: Session, department_id: int, data: schemas.DepartmentUpdate) -> models.Department:
        dep = RecruitmentUseCases.get_department(db, department_id)
        for k, v in _jsonable(data.model_dump(exclude_unset=True)).items():
            setattr(dep, k, v)
        db.commit()
        db.refresh(dep)
        return dep

    @staticmethod
    def set_department_calendly(db: Session, department_id: int, url: str) -> models.Department:
        dep = RecruitmentUseCases.get_department(db, department_id)
        dep.calendly_link = url
        db.commit()
        db.refresh(dep)
        return dep

    @staticmethod
    def set_department_criteria(db: Session, department_id: int, criteria: list) -> models.Department:
        dep = RecruitmentUseCases.get_department(db, department_id)
        dep.scoring_criteria = _jsonable(criteria)
        db.commit()
        db.refresh(dep)
        return dep

    @staticmethod
    def set_department_questions(db: Session, department_id: int, questions: list) -> models.Department:
        dep = RecruitmentUseCases.get_department(db, department_id)
        dep.custom_questions = _jsonable(questions)
        db.commit()
        db.refresh(dep)
        return dep

    # ── Cohorts (recruitment cycles) ────────────────────────────────────────
    @staticmethod
    def list_cycles(db: Session) -> list[models.RecruitmentCycle]:
        return db.query(models.RecruitmentCycle).order_by(models.RecruitmentCycle.created_at.desc()).all()

    @staticmethod
    def get_cycle(db: Session, cycle_id: int) -> models.RecruitmentCycle:
        cycle = db.query(models.RecruitmentCycle).filter(models.RecruitmentCycle.cycle_id == cycle_id).first()
        if not cycle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found")
        return cycle

    @staticmethod
    def get_active_cycle(db: Session) -> models.RecruitmentCycle | None:
        return db.query(models.RecruitmentCycle).filter(models.RecruitmentCycle.is_active.is_(True)).first()

    @staticmethod
    def create_cycle(db: Session, data: schemas.RecruitmentCycleCreate, created_by_user_id) -> models.RecruitmentCycle:
        cycle = models.RecruitmentCycle(
            name=data.name,
            opens_at=data.opens_at,
            closes_at=data.closes_at,
            created_by_user_id=created_by_user_id,
        )
        db.add(cycle)
        db.flush()  # get cycle_id before adding memberships
        RecruitmentUseCases._sync_cycle_departments(db, cycle, data.departments)
        db.commit()
        db.refresh(cycle)
        return cycle

    @staticmethod
    def update_cycle(db: Session, cycle_id: int, data: schemas.RecruitmentCycleUpdate) -> models.RecruitmentCycle:
        cycle = RecruitmentUseCases.get_cycle(db, cycle_id)
        if data.name is not None:
            cycle.name = data.name
        if data.opens_at is not None:
            cycle.opens_at = data.opens_at
        if data.closes_at is not None:
            cycle.closes_at = data.closes_at
        if data.is_active is not None:
            if data.is_active:
                RecruitmentUseCases._deactivate_all(db, except_id=cycle_id)
            cycle.is_active = data.is_active
        if data.departments is not None:
            RecruitmentUseCases._sync_cycle_departments(db, cycle, data.departments)
        db.commit()
        db.refresh(cycle)
        return cycle

    @staticmethod
    def activate_cycle(db: Session, cycle_id: int) -> models.RecruitmentCycle:
        cycle = RecruitmentUseCases.get_cycle(db, cycle_id)
        RecruitmentUseCases._deactivate_all(db, except_id=cycle_id)
        cycle.is_active = True
        db.commit()
        db.refresh(cycle)
        return cycle

    @staticmethod
    def delete_cycle(db: Session, cycle_id: int) -> None:
        cycle = RecruitmentUseCases.get_cycle(db, cycle_id)
        db.delete(cycle)
        db.commit()

    @staticmethod
    def _deactivate_all(db: Session, except_id: int | None = None) -> None:
        """Only one cohort is active at a time; the public form keys off it."""
        q = db.query(models.RecruitmentCycle).filter(models.RecruitmentCycle.is_active.is_(True))
        if except_id is not None:
            q = q.filter(models.RecruitmentCycle.cycle_id != except_id)
        for c in q.all():
            c.is_active = False

    @staticmethod
    def _sync_cycle_departments(db: Session, cycle: models.RecruitmentCycle, departments: list[schemas.CycleDepartmentIn]) -> None:
        RecruitmentUseCases._validate_department_close_dates(db, cycle, departments)
        wanted = {d.department_id: d for d in departments}
        existing = {cd.department_id: cd for cd in cycle.cycle_departments}
        # Remove memberships no longer wanted.
        for dep_id, cd in list(existing.items()):
            if dep_id not in wanted:
                db.delete(cd)
        # Add / update the rest.
        for dep_id, d in wanted.items():
            if dep_id in existing:
                existing[dep_id].is_open = d.is_open
                existing[dep_id].closes_at = d.closes_at
            else:
                db.add(models.CycleDepartment(
                    cycle_id=cycle.cycle_id, department_id=dep_id, is_open=d.is_open, closes_at=d.closes_at))

    @staticmethod
    def _validate_department_close_dates(db: Session, cycle: models.RecruitmentCycle, departments: list[schemas.CycleDepartmentIn]) -> None:
        """An early close has to fall inside the cohort; a later one would never apply."""
        problems = []
        for d in departments:
            if not d.closes_at:
                continue
            if cycle.closes_at and d.closes_at > cycle.closes_at:
                problems.append((d.department_id, "is after the cohort closes"))
            elif cycle.opens_at and d.closes_at <= cycle.opens_at:
                problems.append((d.department_id, "is before the cohort opens"))
        if not problems:
            return
        names = {
            dep.department_id: dep.name for dep in
            db.query(models.Department).filter(models.Department.department_id.in_([p[0] for p in problems])).all()
        }
        detail = "; ".join(f"{names.get(dep_id, f'Department {dep_id}')}'s close date {why}" for dep_id, why in problems)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{detail}.")

    # ── Recruiter → department scoping ──────────────────────────────────────
    @staticmethod
    def get_recruiter_departments(db: Session, user_id) -> list[int]:
        rows = (
            db.query(models.RecruiterDepartment.department_id)
            .filter(models.RecruiterDepartment.user_id == user_id)
            .all()
        )
        return [r[0] for r in rows]

    @staticmethod
    def set_recruiter_departments(db: Session, user_id, department_ids: list[int]) -> list[int]:
        db.query(models.RecruiterDepartment).filter(models.RecruiterDepartment.user_id == user_id).delete()
        for dep_id in set(department_ids):
            db.add(models.RecruiterDepartment(user_id=user_id, department_id=dep_id))
        db.commit()
        return RecruitmentUseCases.get_recruiter_departments(db, user_id)


def _jsonable(value):
    """Recursively convert Pydantic models to plain dicts for JSONB columns."""
    from pydantic import BaseModel
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value
