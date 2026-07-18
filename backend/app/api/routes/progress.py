from fastapi import APIRouter
from app.db.crud import get_all_learner_concepts

router = APIRouter()


# {user_id} in the path is a PATH PARAMETER — FastAPI automatically extracts
# whatever's in that URL segment and passes it as the user_id argument below.
# get_all_learner_concepts already fills in defaults for untouched concepts,
# so the frontend always gets a full list, even for a brand-new learner.
@router.get("/progress/{user_id}")
def progress(user_id: str):
    concepts = get_all_learner_concepts(user_id)
    return {"concepts": concepts}