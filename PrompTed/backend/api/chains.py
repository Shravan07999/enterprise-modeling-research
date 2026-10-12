from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from database import get_session
from models import Chain, ChainStep, ChainRead
from sqlalchemy.orm import selectinload

router = APIRouter(
    prefix="/chains",
    tags=["chains"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", response_model=ChainRead)
def create_chain(chain: Chain, session: Session = Depends(get_session)):
    session.add(chain)
    session.commit()
    session.refresh(chain)
    return chain


@router.post("/{chain_id}/steps", response_model=ChainStep)
def add_step(chain_id: int, step: ChainStep, session: Session = Depends(get_session)):
    step.chain_id = chain_id
    session.add(step)
    session.commit()
    session.refresh(step)
    return step


@router.get("/", response_model=List[ChainRead])
def read_chains(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_session)
):
    statement = (
        select(Chain)
        .offset(skip)
        .limit(limit)
        .options(selectinload(Chain.steps).selectinload(ChainStep.prompt))
    )
    chains = session.exec(statement).all()
    return chains


@router.get("/{chain_id}", response_model=ChainRead)
def read_chain(chain_id: int, session: Session = Depends(get_session)):
    statement = (
        select(Chain)
        .where(Chain.id == chain_id)
        .options(selectinload(Chain.steps).selectinload(ChainStep.prompt))
    )
    chain = session.exec(statement).first()
    if not chain:
        raise HTTPException(status_code=404, detail="Chain not found")
    return chain


@router.patch("/{chain_id}", response_model=ChainRead)
def update_chain(
    chain_id: int, chain_data: dict, session: Session = Depends(get_session)
):
    db_chain = session.get(Chain, chain_id)
    if not db_chain:
        raise HTTPException(status_code=404, detail="Chain not found")

    for key, value in chain_data.items():
        if key != "steps":
            setattr(db_chain, key, value)

    if "steps" in chain_data:
        from models import ChainStep

        statement = select(ChainStep).where(ChainStep.chain_id == chain_id)
        old_steps = session.exec(statement).all()
        for old_step in old_steps:
            session.delete(old_step)

        for step in chain_data["steps"]:
            new_step = ChainStep(
                chain_id=chain_id,
                prompt_id=step["prompt_id"],
                order=step["order"],
                input_mapping=step.get("input_mapping"),
            )
            session.add(new_step)

    session.add(db_chain)
    session.commit()
    session.refresh(db_chain)

    statement = (
        select(Chain)
        .where(Chain.id == chain_id)
        .options(selectinload(Chain.steps).selectinload(ChainStep.prompt))
    )
    return session.exec(statement).first()


@router.delete("/{chain_id}")
def delete_chain(chain_id: int, session: Session = Depends(get_session)):
    chain = session.get(Chain, chain_id)
    if not chain:
        raise HTTPException(status_code=404, detail="Chain not found")
    session.delete(chain)
    session.commit()
    return {"ok": True}
