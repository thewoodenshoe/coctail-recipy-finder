from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Creator(Base):
    __tablename__ = "creators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    handle: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    profile_url: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    backfill_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sync_status: Mapped[str] = mapped_column(String(64), default="never_synced", nullable=False)
    sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    posts: Mapped[list["Post"]] = relationship(back_populates="creator")


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("creators.id"), nullable=False)
    source_platform: Mapped[str] = mapped_column(String(64), default="instagram", nullable=False)
    source_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    external_post_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    caption_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    raw_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    creator: Mapped[Creator] = relationship(back_populates="posts")
    recipe: Mapped["Recipe"] = relationship(
        back_populates="post", cascade="all, delete-orphan", uselist=False
    )


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), unique=True, nullable=False)
    drink_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    base_spirit: Mapped[str | None] = mapped_column(String(128), nullable=True)
    base_spirits_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    ingredients_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    method: Mapped[str | None] = mapped_column(Text, nullable=True)
    garnish: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_instagram_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)

    post: Mapped[Post] = relationship(back_populates="recipe")


class RawPost(Base):
    __tablename__ = "raw_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(64), default="instagram", nullable=False)
    creator_id: Mapped[int] = mapped_column(ForeignKey("creators.id"), nullable=False)
    creator_handle_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    external_post_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    raw_caption_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    raw_intro_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_hashtags_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    raw_view_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_like_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_comment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    capture_completeness: Mapped[str] = mapped_column(String(64), default="text_only", nullable=False)
    ingestion_provider: Mapped[str] = mapped_column(String(128), default="legacy_migration", nullable=False)
    ingestion_status: Mapped[str] = mapped_column(String(64), default="raw_captured", nullable=False)
    ingestion_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class RecipeExtraction(Base):
    __tablename__ = "recipe_extractions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_post_id: Mapped[int] = mapped_column(ForeignKey("raw_posts.id"), nullable=False, index=True)
    transformer_name: Mapped[str] = mapped_column(String(128), nullable=False)
    transformer_version: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    extracted_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_reasons_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class GoldRecipe(Base):
    __tablename__ = "gold_recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_post_id: Mapped[int] = mapped_column(ForeignKey("raw_posts.id"), unique=True, nullable=False)
    extraction_id: Mapped[int | None] = mapped_column(ForeignKey("recipe_extractions.id"), nullable=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("creators.id"), nullable=False)
    creator_handle: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    drink_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    drink_title_normalized: Mapped[str | None] = mapped_column(String(255), nullable=True)
    intro_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_spirits_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    ingredients_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    method: Mapped[str | None] = mapped_column(Text, nullable=True)
    garnish: Mapped[str | None] = mapped_column(Text, nullable=True)
    glassware: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tags_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    view_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    like_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    transformed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    transformer_version: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), default="active", nullable=False)
