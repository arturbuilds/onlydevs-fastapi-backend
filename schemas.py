from pydantic import BaseModel, Field, field_validator

class AuthorCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)

class PostCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=100)
    secret_content: str = Field(..., min_length=1)
    price: int = Field(..., ge=0, description='Цена поста в коинах/гривнах')
    author_id: int

    @field_validator('title')
    @classmethod
    def check_bad_words(cls, v: str) -> str:
        bad_words = ['скам', 'слив', 'cheat']
        for word in bad_words:
            if word in v.lower():
                raise ValueError(f"В заголовке запрещено использовать слово: {word}")
        return v