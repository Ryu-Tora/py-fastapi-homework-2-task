from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class MovieCreate(BaseModel):
    name: str = Field(..., max_length=255)
    date: date
    score: float = Field(..., ge=0, le=100)
    overview: str
    status: str
    budget: float = Field(..., ge=0)
    revenue: float = Field(..., ge=0)
    country: str

    genres: list[str]
    actors: list[str]
    languages: list[str]

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: date):
        if value > date.today().replace(year=date.today().year + 1):
            raise ValueError(
                "Date must not be more than one year in the future"
            )
        return value


class IdNameSchema(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class CountrySchema(BaseModel):
    id: int
    code: str
    name: Optional[str]

    class Config:
        from_attributes = True


class MovieDetailSchema(BaseModel):
    id: int
    name: str
    date: date
    score: float
    overview: str
    status: str
    budget: float
    revenue: float

    country: CountrySchema
    genres: list[IdNameSchema]
    actors: list[IdNameSchema]
    languages: list[IdNameSchema]

    class Config:
        from_attributes = True


class MovieListItemSchema(BaseModel):
    id: int
    name: str
    date: date
    score: float
    overview: str

    class Config:
        from_attributes = True


class MovieListResponseSchema(BaseModel):
    movies: List[MovieListItemSchema]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int


class MovieUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    date: Optional[date]
    score: Optional[float] = Field(None, ge=0, le=100)
    overview: Optional[str]
    status: Optional[str]
    budget: Optional[float] = Field(None, ge=0)
    revenue: Optional[float] = Field(None, ge=0)

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: date):
        if value and value > date.today().replace(year=date.today().year + 1):
            raise ValueError("Date must not be more than one year in the future")
        return value
