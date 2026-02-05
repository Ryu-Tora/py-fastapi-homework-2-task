import math

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request
)
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from schemas.movies import (
    MovieCreate,
    MovieUpdateSchema,
    MovieDetailSchema,
    MovieListResponseSchema
)
from src.database import get_db
from src.database.models import (
    CountryModel,
    GenreModel,
    ActorModel,
    LanguageModel,
    MovieModel
)
from starlette import status


router = APIRouter()


async def get_or_create(
        model: BaseModel,
        db,
        *,
        name: str | None = None,
        code: str | None = None,
):
    obj = select(model)
    if name is not None and hasattr(model, "name"):
        obj = obj.where(model.name == name)

    if code is not None and hasattr(model, "code"):
        obj = obj.where(model.code == code)

    result = await db.execute(obj)
    instance = result.scalar_one_or_none()

    if instance:
        return instance

    kwargs = {}
    if code is not None and hasattr(model, "code"):
        kwargs["code"] = code
    if name is not None and hasattr(model, "name"):
        kwargs["name"] = name

    instance = model(**kwargs)

    db.add(instance)
    await db.commit()
    await db.refresh(instance)
    return instance


@router.get("/movies/", response_model=MovieListResponseSchema)
async def get_movies(
        db: AsyncSession = Depends(get_db),
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1, le=20)
):
    offset = (page - 1) * per_page

    result = await db.execute(
        select(MovieModel)
        .order_by(MovieModel.id.desc())
        .limit(per_page)
        .offset(offset)
    )
    movies = result.scalars().all()

    if not movies:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No movies found.")

    total_result = await db.execute(select(func.count()).select_from(MovieModel))
    total_items = total_result.scalar()
    total_pages = math.ceil(total_items / per_page) if total_items else 1

    prev_page = f"/theater/movies/?page={page - 1}&per_page={per_page}"\
        if page > 1 \
        else None
    next_page = f"/theater/movies/?page={page + 1}&per_page={per_page}"\
        if page < total_pages \
        else None

    return {
        "movies": movies,
        "prev_page": prev_page,
        "next_page": next_page,
        "total_pages": total_pages,
        "total_items": total_items,
    }


@router.post("/movies/", response_model=MovieDetailSchema, status_code=status.HTTP_201_CREATED)
async def create_movie(new_movie: MovieCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MovieModel).where(
            MovieModel.name == new_movie.name,
            MovieModel.date == new_movie.date,
        )
    )

    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A movie with the name '{new_movie.name}' and release date '{new_movie.date}' already exists."
        )

    country = await get_or_create(CountryModel, db, code=new_movie.country)

    movie = MovieModel(
        name=new_movie.name,
        date=new_movie.date,
        score=new_movie.score,
        overview=new_movie.overview,
        status=new_movie.status,
        budget=new_movie.budget,
        revenue=new_movie.revenue,
        country=country
    )

    db.add(movie)
    await db.flush()

    genres = []
    for genre_name in new_movie.genres:
        g = await get_or_create(GenreModel, db, name=genre_name)
        genres.append(g)
    movie.genres = genres

    actors = []
    for actor_name in new_movie.actors:
        g = await get_or_create(ActorModel, db, name=actor_name)
        actors.append(g)
    movie.actors = actors

    languages = []
    for language_name in new_movie.languages:
        g = await get_or_create(LanguageModel, db, name=language_name)
        languages.append(g)
    movie.languages = languages

    await db.commit()
    await db.refresh(movie)
    return movie


@router.get("/movies/{movie_id}/", response_model=MovieDetailSchema, status_code=status.HTTP_200_OK)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MovieModel).where(MovieModel.id == movie_id)
        .options(
            selectinload(MovieModel.country),
            selectinload(MovieModel.genres),
            selectinload(MovieModel.actors),
            selectinload(MovieModel.languages),
        )
    )

    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie with the given ID was not found."
        )

    return movie


@router.delete("/movies/{movie_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await get_movie(movie_id, db)
    await db.delete(movie)
    await db.commit()


@router.patch("/movies/{movie_id}/")
async def update_movie(movie_id: int, data: MovieUpdateSchema, db: AsyncSession = Depends(get_db)):
    movie = await get_movie(movie_id, db)

    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input data."
        )

    for field, value in update_data.items():
        setattr(movie, field, value)

    await db.commit()

    return {"detail": "Movie updated successfully."}
