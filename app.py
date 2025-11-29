import os
import re
import sqlite3
from collections.abc import Sequence
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import (Flask, flash, g, redirect, render_template, request,
                   session, url_for)
from flask_mail import Mail, Message
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

LEAD_STATUSES = [
    "New",
    "Contacted",
    "In Progress",
    "Qualified",
    "Closed",
]

DEFAULT_PAGE_SEEDS: list[dict[str, str | int | None]] = [
    {
        "slug": "home",
        "page_name": "Homepage",
        "template_name": "index.html",
        "nav_order": 10,
        "nav_display": "hidden",
        "seo_title": "London Maths & Science College | Specialist STEM Sixth Form",
        "meta_description": (
            "Discover London Maths & Science College, a specialist 16–19 STEM sixth form in London "
            "offering A Levels, GCSEs and clear routes to top universities."
        ),
    },
    {
        "slug": "about",
        "page_name": "About LMSC",
        "template_name": "about.html",
        "nav_order": 20,
        "nav_display": "footer",
        "seo_title": "About London Maths & Science College | Who We Are",
        "meta_description": (
            "Learn about our mission, values and leadership at London Maths & Science College, the "
            "specialist STEM sixth form for ambitious 16–19 students."
        ),
    },
    {
        "slug": "stem-pathways",
        "page_name": "STEM Pathways",
        "template_name": "stem_pathways.html",
        "nav_order": 30,
        "nav_display": "footer",
        "seo_title": "STEM Pathways | A Level & GCSE Courses at LMSC",
        "meta_description": (
            "Explore the specialist STEM pathways at LMSC, from A Level Mathematics and Sciences to "
            "GCSE resits designed to support progression into competitive degrees."
        ),
    },
    {
        "slug": "study-options",
        "page_name": "Study Options",
        "template_name": "study_options.html",
        "nav_order": 40,
        "nav_display": "footer",
        "seo_title": "Study Options | Learn Online or On Campus with LMSC",
        "meta_description": (
            "See the flexible study options at LMSC, combining online lessons and in-person teaching so "
            "every student can access the STEM programme that fits their life."
        ),
    },
    {
        "slug": "fees",
        "page_name": "Fees & Finance",
        "template_name": "fees.html",
        "nav_order": 50,
        "nav_display": "footer",
        "seo_title": "Fees & Finance | London Maths & Science College",
        "meta_description": (
            "Review tuition fees, funding information and payment schedules for London Maths & Science "
            "College to plan your investment in specialist STEM teaching."
        ),
    },
    {
        "slug": "how-we-teach",
        "page_name": "How We Teach",
        "template_name": "how_we_teach.html",
        "nav_order": 60,
        "nav_display": "footer",
        "seo_title": "How We Teach STEM | London Maths & Science College",
        "meta_description": (
            "Understand how LMSC blends subject mastery, structured practice and one-to-one support to "
            "deliver exceptional STEM teaching on campus and online."
        ),
    },
    {
        "slug": "our-teacher-experts",
        "page_name": "Our Teacher Experts",
        "template_name": "our_teacher_expert.html",
        "nav_order": 70,
        "nav_display": "footer",
        "seo_title": "Our Teachers & Expert Tutors | LMSC Faculty",
        "meta_description": (
            "Meet the specialist STEM teachers and tutors at LMSC who deliver expert instruction, "
            "mentoring and exam preparation across Maths, Sciences and Computing."
        ),
    },
    {
        "slug": "informed-teaching",
        "page_name": "Informed Teaching",
        "template_name": "informed_teaching.html",
        "nav_order": 80,
        "nav_display": "footer",
        "seo_title": "Evidence-Informed Teaching | London Maths & Science College",
        "meta_description": (
            "See how LMSC uses evidence-informed strategies, assessment insights and research to shape "
            "high-impact STEM teaching for every student."
        ),
    },
    {
        "slug": "courses",
        "page_name": "Courses",
        "template_name": "courses.html",
        "nav_order": 90,
        "nav_display": "main",
        "seo_title": "Courses at LMSC | Specialist STEM Curriculum",
        "meta_description": (
            "Browse the full STEM course offer at London Maths & Science College, from core A Levels to "
            "tailored pathways that prepare students for top university routes."
        ),
    },
    {
        "slug": "course-details",
        "page_name": "Course Details",
        "template_name": "course_details.html",
        "nav_order": 100,
        "nav_display": "dropdown",
        "nav_parent_slug": "courses",
        "seo_title": "Course Details | London Maths & Science College",
        "meta_description": (
            "Dive into detailed course information for LMSC programmes, including entry requirements, "
            "module highlights and progression opportunities."
        ),
    },
    {
        "slug": "pricing",
        "page_name": "Pricing",
        "template_name": "pricing.html",
        "nav_order": 110,
        "nav_display": "main",
        "seo_title": "Pricing & Payment Plans | LMSC",
        "meta_description": (
            "Compare pricing packages and payment plans for London Maths & Science College to find the "
            "right route into expert STEM tuition."
        ),
    },
    {
        "slug": "blogs",
        "page_name": "Blogs",
        "template_name": "blogs.html",
        "nav_order": 120,
        "nav_display": "footer",
        "seo_title": "LMSC Blog | Insights & Updates",
        "meta_description": (
            "Read the latest articles, insights and stories from London Maths & Science College covering "
            "STEM education, student success and college news."
        ),
    },
    {
        "slug": "blog-details",
        "page_name": "Blog Details",
        "template_name": "blog_details.html",
        "nav_order": 130,
        "nav_display": "hidden",
        "seo_title": "Blog Article | London Maths & Science College",
        "meta_description": (
            "Explore an in-depth article from the LMSC blog sharing guidance, case studies and news from "
            "our specialist STEM sixth form community."
        ),
    },
    {
        "slug": "reviews",
        "page_name": "Reviews",
        "template_name": "reviews.html",
        "nav_order": 140,
        "nav_display": "footer",
        "seo_title": "Student Reviews | London Maths & Science College",
        "meta_description": (
            "Hear from students and families about their experiences studying STEM subjects at LMSC, "
            "including outcomes, support and college life."
        ),
    },
    {
        "slug": "a-level-math",
        "page_name": "A-Level Maths",
        "template_name": "a_level_math.html",
        "nav_order": 150,
        "nav_display": "dropdown",
        "nav_parent_slug": "courses",
        "seo_title": "A Level Maths | London Maths & Science College",
        "meta_description": (
            "Learn how LMSC delivers A Level Mathematics with expert teaching, focused exam preparation "
            "and pathways into STEM degrees."
        ),
    },
    {
        "slug": "our-mission",
        "page_name": "Our Mission",
        "template_name": "our_mission.html",
        "nav_order": 160,
        "nav_display": "footer",
        "seo_title": "Our Mission & Values | London Maths & Science College",
        "meta_description": (
            "Discover the mission, values and ambitions that shape London Maths & Science College as a "
            "forward-thinking STEM sixth form."
        ),
    },
    {
        "slug": "contact",
        "page_name": "Contact",
        "template_name": "contact.html",
        "nav_order": 170,
        "nav_display": "footer",
        "seo_title": "Contact London Maths & Science College",
        "meta_description": (
            "Reach the admissions and support teams at LMSC to discuss courses, entry requirements or "
            "booking a consultation."
        ),
    },
    {
        "slug": "development",
        "page_name": "Development",
        "template_name": "development.html",
        "nav_order": 180,
        "nav_display": "hidden",
        "seo_title": "New Content Coming Soon | London Maths & Science College",
        "meta_description": (
            "This page is being developed. Check back soon for new information from London Maths & Science College."
        ),
    },
    {
        "slug": "policies",
        "page_name": "School Policies",
        "template_name": "policies.html",
        "nav_order": 190,
        "nav_display": "footer",
        "seo_title": "School Policies & Documents | LMSC",
        "meta_description": (
            "Access statutory policies, safeguarding documents and official reports from London Maths & Science College."
        ),
    },
]

DEFAULT_ADMIN_USERNAME = "info@lmsc.org.uk"
DEFAULT_ADMIN_PASSWORD = "LMSC@dmin2025"
GMAIL_APP_PASSWORD = "xkal uhnp xqto hvyz"

PAGE_ENDPOINT_OVERRIDES: dict[str, str] = {
    "home": "index",
    "about": "about",
    "stem-pathways": "stem_pathways",
    "study-options": "study_options",
    "fees": "fees",
    "how-we-teach": "how_we_teach",
    "our-teacher-experts": "our_teacher_expert",
    "informed-teaching": "informed_teaching",
    "courses": "courses",
    "course-details": "course_details",
    "pricing": "pricing",
    "blogs": "blogs",
    "blog-details": "blog_details",
    "reviews": "reviews",
    "a-level-math": "a_level_math",
    "our-mission": "our_mission",
    "contact": "contact",
    "development": "development",
    "policies": "policies_page",
}


mail = Mail()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret")

    template_root = Path(app.root_path) / "templates"
    pages_template_dir = template_root / "pages"
    pages_template_dir.mkdir(parents=True, exist_ok=True)
    app.config["PAGES_TEMPLATE_DIR"] = str(pages_template_dir)

    uploads_dir = Path(app.root_path) / "static" / "uploads" / "social"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.config["SOCIAL_IMAGE_UPLOAD_FOLDER"] = str(uploads_dir)

    policy_docs_dir = Path(app.root_path) / "static" / "uploads" / "policies" / "documents"
    policy_thumbs_dir = Path(app.root_path) / "static" / "uploads" / "policies" / "thumbnails"
    policy_docs_dir.mkdir(parents=True, exist_ok=True)
    policy_thumbs_dir.mkdir(parents=True, exist_ok=True)

    app.config["POLICY_DOC_UPLOAD_FOLDER"] = str(policy_docs_dir)
    app.config["POLICY_THUMB_UPLOAD_FOLDER"] = str(policy_thumbs_dir)

    app.config["ALLOWED_IMAGE_EXTENSIONS"] = {"jpg", "jpeg", "png", "webp", "gif"}
    app.config["ALLOWED_POLICY_DOC_EXTENSIONS"] = {"pdf"}

    app.config["MAIL_SERVER"] = "smtp.gmail.com"
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USE_SSL"] = False
    app.config["MAIL_USERNAME"] = DEFAULT_ADMIN_USERNAME
    app.config["MAIL_PASSWORD"] = GMAIL_APP_PASSWORD
    app.config["MAIL_DEFAULT_SENDER"] = ("London Maths & Science College", DEFAULT_ADMIN_USERNAME)
    app.config["MAIL_SUPPRESS_SEND"] = False
    app.config["MAIL_ASCII_ATTACHMENTS"] = True

    mail.init_app(app)

    def send_email(
        subject: str,
        recipients: Sequence[str],
        *,
        body: str | None = None,
        html: str | None = None,
        sender: str | tuple[str, str] | None = None,
    ) -> None:
        if not recipients:
            raise ValueError("At least one recipient is required.")

        message = Message(
            subject=subject,
            recipients=list(recipients),
            sender=sender or app.config["MAIL_DEFAULT_SENDER"],
        )

        if body:
            message.body = body
        if html:
            message.html = html

        mail.send(message)

    app.send_email = send_email  # type: ignore[attr-defined]

    instance_path = Path(app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)
    app.config["DATABASE"] = str(instance_path / "lmsc.sqlite3")

    def slugify(value: str) -> str:
        value = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().lower())
        value = re.sub(r"-+", "-", value).strip("-")
        return value or "page"

    def generate_unique_slug(base_slug: str) -> str:
        slug = base_slug
        suffix = 1
        db = get_db()
        while (
            db.execute("SELECT 1 FROM pages WHERE slug = ?", (slug,)).fetchone()
            is not None
        ):
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        return slug

    def allowed_image_file(filename: str) -> bool:
        if not filename or "." not in filename:
            return False
        ext = filename.rsplit(".", 1)[1].lower()
        return ext in app.config["ALLOWED_IMAGE_EXTENSIONS"]

    def save_social_image(file_storage) -> str | None:
        if not file_storage or not file_storage.filename:
            return None
        if not allowed_image_file(file_storage.filename):
            raise ValueError("Unsupported image format. Please upload JPG, PNG, WEBP, or GIF.")

        filename = secure_filename(file_storage.filename)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        final_name = f"{timestamp}_{filename}"
        destination = Path(app.config["SOCIAL_IMAGE_UPLOAD_FOLDER"]) / final_name
        file_storage.save(destination)
        return f"uploads/social/{final_name}"

    def allowed_policy_document(filename: str) -> bool:
        if not filename or "." not in filename:
            return False
        ext = filename.rsplit(".", 1)[1].lower()
        return ext in app.config["ALLOWED_POLICY_DOC_EXTENSIONS"]

    def save_policy_document(file_storage):
        if not file_storage or not file_storage.filename:
            raise ValueError("Please choose a policy document to upload.")
        if not allowed_policy_document(file_storage.filename):
            raise ValueError("Policy documents must be supplied as PDF files.")

        filename = secure_filename(file_storage.filename)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        final_name = f"{timestamp}_{filename}"
        destination = Path(app.config["POLICY_DOC_UPLOAD_FOLDER"]) / final_name
        file_storage.save(destination)
        return f"uploads/policies/documents/{final_name}"

    def save_policy_thumbnail(file_storage) -> str | None:
        if not file_storage or not file_storage.filename:
            return None
        if not allowed_image_file(file_storage.filename):
            raise ValueError("Policy thumbnails must be JPG, JPEG, PNG, WEBP, or GIF files.")

        filename = secure_filename(file_storage.filename)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        final_name = f"{timestamp}_{filename}"
        destination = Path(app.config["POLICY_THUMB_UPLOAD_FOLDER"]) / final_name
        file_storage.save(destination)
        return f"uploads/policies/thumbnails/{final_name}"

    def remove_static_file(relative_path: str | None) -> None:
        if not relative_path:
            return
        target_path = Path(app.root_path) / "static" / relative_path
        try:
            target_path.unlink(missing_ok=True)
        except OSError:
            pass

    def guess_policy_title_from_filename(filename: str) -> str:
        stem = Path(filename).stem
        cleaned = re.sub(r"[_\-]+", " ", stem)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned.title() if cleaned else "School Policy"

    def available_templates() -> list[str]:
        templates: list[str] = []
        for html_path in template_root.rglob("*.html"):
            rel = html_path.relative_to(template_root).as_posix()
            if rel.startswith("admin/"):
                continue
            templates.append(rel)
        templates.sort()
        return templates

    def get_db() -> sqlite3.Connection:
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(exception: Exception | None = None) -> None:
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def current_timestamp() -> str:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    def init_db() -> None:
        db = get_db()
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_type TEXT NOT NULL,
                full_name TEXT,
                email TEXT,
                phone TEXT,
                message TEXT,
                source TEXT,
                status TEXT NOT NULL DEFAULT 'New',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                page_name TEXT NOT NULL,
                seo_title TEXT,
                meta_description TEXT,
                nav_display TEXT NOT NULL DEFAULT 'hidden',
                nav_parent_id INTEGER,
                nav_order INTEGER NOT NULL DEFAULT 0,
                social_image TEXT,
                template_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (nav_parent_id) REFERENCES pages (id)
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_pages_nav_display ON pages(nav_display)"
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_pages_nav_parent ON pages(nav_parent_id)"
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                document_path TEXT NOT NULL,
                thumbnail_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_policies_title ON policies(title)"
        )
        db.commit()

    def ensure_default_admin() -> None:
        db = get_db()
        row = db.execute(
            "SELECT id FROM users WHERE username = ?", (DEFAULT_ADMIN_USERNAME,)
        ).fetchone()
        if row is None:
            db.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (
                    DEFAULT_ADMIN_USERNAME,
                    generate_password_hash(DEFAULT_ADMIN_PASSWORD),
                    current_timestamp(),
                ),
            )
            db.commit()

    def seed_existing_pages() -> None:
        db = get_db()
        placement_choices = {"main", "dropdown", "footer", "hidden"}

        for seed in DEFAULT_PAGE_SEEDS:
            slug = str(seed["slug"])
            page_name = str(seed["page_name"])
            template_name = str(seed["template_name"])
            nav_order = int(seed.get("nav_order", 0))
            nav_display = str(seed.get("nav_display") or "hidden")
            if nav_display not in placement_choices:
                nav_display = "hidden"

            seo_title = seed.get("seo_title")
            meta_description = seed.get("meta_description")

            existing = db.execute(
                "SELECT * FROM pages WHERE slug = ?",
                (slug,),
            ).fetchone()

            if existing is None:
                now = current_timestamp()
                db.execute(
                    """
                    INSERT INTO pages (
                        slug,
                        page_name,
                        seo_title,
                        meta_description,
                        nav_display,
                        nav_parent_id,
                        nav_order,
                        social_image,
                        template_name,
                        created_at,
                        updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, NULL, ?, NULL, ?, ?, ?)
                    """,
                    (
                        slug,
                        page_name,
                        seo_title,
                        meta_description,
                        nav_display,
                        nav_order,
                        template_name,
                        now,
                        now,
                    ),
                )
                continue

            updates: list[str] = []
            params: list[object] = []

            if seo_title and not existing["seo_title"]:
                updates.append("seo_title = ?")
                params.append(seo_title)

            if meta_description and not existing["meta_description"]:
                updates.append("meta_description = ?")
                params.append(meta_description)

            if nav_display != "hidden" and existing["nav_display"] == "hidden":
                updates.append("nav_display = ?")
                params.append(nav_display)

            if nav_order and existing["nav_order"] == 0:
                updates.append("nav_order = ?")
                params.append(nav_order)

            if page_name and existing["page_name"] == existing["slug"]:
                updates.append("page_name = ?")
                params.append(page_name)

            existing_template = existing["template_name"]
            if (
                template_name
                and isinstance(existing_template, str)
                and existing_template.startswith("pages/")
                and existing_template != template_name
            ):
                updates.append("template_name = ?")
                params.append(template_name)

            if updates:
                updates.append("updated_at = ?")
                params.append(current_timestamp())
                params.append(existing["id"])
                db.execute(
                    f"UPDATE pages SET {', '.join(updates)} WHERE id = ?",
                    params,
                )

        db.commit()

        for seed in DEFAULT_PAGE_SEEDS:
            nav_parent_slug = seed.get("nav_parent_slug")
            if not nav_parent_slug:
                continue

            child = db.execute(
                "SELECT id, nav_parent_id FROM pages WHERE slug = ?",
                (seed["slug"],),
            ).fetchone()
            parent = db.execute(
                "SELECT id FROM pages WHERE slug = ?",
                (nav_parent_slug,),
            ).fetchone()

            if child is None or parent is None:
                continue

            if child["nav_parent_id"] == parent["id"]:
                continue

            db.execute(
                "UPDATE pages SET nav_parent_id = ?, updated_at = ? WHERE id = ?",
                (parent["id"], current_timestamp(), child["id"]),
            )

        db.commit()

    def fetch_all_leads() -> list[sqlite3.Row]:
        db = get_db()
        return db.execute(
            "SELECT * FROM leads ORDER BY datetime(created_at) DESC"
        ).fetchall()

    def fetch_all_pages() -> list[sqlite3.Row]:
        db = get_db()
        return db.execute(
            "SELECT * FROM pages ORDER BY nav_order ASC, page_name ASC"
        ).fetchall()

    def fetch_all_policies() -> list[sqlite3.Row]:
        db = get_db()
        return db.execute(
            "SELECT * FROM policies ORDER BY LOWER(title) ASC, title ASC"
        ).fetchall()

    def get_policy(policy_id: int) -> sqlite3.Row | None:
        db = get_db()
        return db.execute(
            "SELECT * FROM policies WHERE id = ?",
            (policy_id,),
        ).fetchone()

    def create_policy_record(
        *, title: str, document_path: str, thumbnail_path: str | None
    ) -> None:
        db = get_db()
        now = current_timestamp()
        db.execute(
            """
            INSERT INTO policies (title, document_path, thumbnail_path, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, document_path, thumbnail_path, now, now),
        )
        db.commit()

    @app.context_processor
    def inject_navigation() -> dict[str, object]:
        try:
            pages = fetch_all_pages()
        except sqlite3.Error:
            return {}

        main_pages = [page for page in pages if page["nav_display"] == "main"]
        dropdown_pages = [page for page in pages if page["nav_display"] == "dropdown"]
        footer_pages = [page for page in pages if page["nav_display"] == "footer"]

        grouped_children: dict[int, list[sqlite3.Row]] = {}
        for child in dropdown_pages:
            parent_id = child["nav_parent_id"]
            if parent_id is None:
                continue
            grouped_children.setdefault(parent_id, []).append(child)

        for children in grouped_children.values():
            children.sort(key=lambda row: (row["nav_order"], row["page_name"]))

        page_lookup = {page["id"]: page for page in pages}

        dropdown_groups: list[dict[str, object]] = []
        dropdown_lookup: dict[int, list[sqlite3.Row]] = {}
        for parent_id, children in grouped_children.items():
            parent = page_lookup.get(parent_id)
            if parent is None:
                continue
            dropdown_groups.append({"parent": parent, "children": children})
            dropdown_lookup[parent_id] = children

        dropdown_groups.sort(
            key=lambda group: (
                group["parent"]["nav_order"],
                group["parent"]["page_name"],
            )
        )

        main_ids = {page["id"] for page in main_pages}
        standalone_dropdowns = [
            group for group in dropdown_groups if group["parent"]["id"] not in main_ids
        ]

        footer_pages.sort(key=lambda row: (row["nav_order"], row["page_name"]))

        def build_page_url(page_row: sqlite3.Row) -> str:
            endpoint = PAGE_ENDPOINT_OVERRIDES.get(page_row["slug"])
            if endpoint:
                try:
                    return url_for(endpoint)
                except Exception:
                    pass
            return url_for("render_dynamic_page", slug=page_row["slug"])

        managed_urls = {page["id"]: build_page_url(page) for page in pages}

        return {
            "nav_pages_main": main_pages,
            "nav_pages_dropdown": dropdown_groups,
            "nav_pages_dropdown_lookup": dropdown_lookup,
            "nav_pages_dropdown_standalone": standalone_dropdowns,
            "nav_pages_footer": footer_pages,
            "nav_managed_page_urls": managed_urls,
        }

    def get_page_by_slug(slug: str) -> sqlite3.Row | None:
        db = get_db()
        return db.execute("SELECT * FROM pages WHERE slug = ?", (slug,)).fetchone()

    def get_page_by_id(page_id: int) -> sqlite3.Row | None:
        db = get_db()
        return db.execute("SELECT * FROM pages WHERE id = ?", (page_id,)).fetchone()

    def render_site_page(template_name: str, slug: str, **context) -> str:
        page_record = get_page_by_slug(slug)
        if page_record is not None:
            page_dict = dict(page_record)
            page_name = page_dict.get("page_name")
            if page_name and not page_dict.get("seo_title"):
                page_dict["seo_title"] = f"{page_name} | London Maths & Science College"
            if page_name and not page_dict.get("meta_description"):
                page_dict["meta_description"] = (
                    f"Learn more about {page_name} at London Maths & Science College."
                )
            context.setdefault("page", page_dict)
            context.setdefault("page_meta", page_dict)
        else:
            context.setdefault("page_meta", None)
        return render_template(template_name, **context)

    def upsert_page(
        *,
        page_id: int | None,
        slug: str,
        page_name: str,
        seo_title: str | None,
        meta_description: str | None,
        nav_display: str,
        nav_parent_id: int | None,
        nav_order: int,
        social_image: str | None,
        template_name: str,
    ) -> int:
        db = get_db()
        now = current_timestamp()

        if page_id is None:
            cursor = db.execute(
                """
                INSERT INTO pages (
                    slug,
                    page_name,
                    seo_title,
                    meta_description,
                    nav_display,
                    nav_parent_id,
                    nav_order,
                    social_image,
                    template_name,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    slug,
                    page_name,
                    seo_title,
                    meta_description,
                    nav_display,
                    nav_parent_id,
                    nav_order,
                    social_image,
                    template_name,
                    now,
                    now,
                ),
            )
            db.commit()
            return int(cursor.lastrowid)

        db.execute(
            """
            UPDATE pages
            SET page_name = ?,
                seo_title = ?,
                meta_description = ?,
                nav_display = ?,
                nav_parent_id = ?,
                nav_order = ?,
                social_image = ?,
                template_name = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                page_name,
                seo_title,
                meta_description,
                nav_display,
                nav_parent_id,
                nav_order,
                social_image,
                template_name,
                now,
                page_id,
            ),
        )
        db.commit()
        return page_id

    def create_lead(
        lead_type: str,
        *,
        full_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        message: str | None = None,
        source: str | None = None,
    ) -> None:
        db = get_db()
        timestamp = current_timestamp()
        db.execute(
            """
            INSERT INTO leads (lead_type, full_name, email, phone, message, source, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'New', ?, ?)
            """,
            (lead_type, full_name, email, phone, message, source, timestamp, timestamp),
        )
        db.commit()

    def update_lead_status_db(lead_id: int, status: str) -> None:
        db = get_db()
        db.execute(
            "UPDATE leads SET status = ?, updated_at = ? WHERE id = ?",
            (status, current_timestamp(), lead_id),
        )
        db.commit()

    def login_required(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if session.get("user_id") is None:
                flash("Please sign in to access the dashboard.", "warning")
                return redirect(url_for("admin_login", next=request.path))
            return view(*args, **kwargs)

        return wrapped_view

    def safe_next(target: str | None) -> str | None:
        if target and target.startswith("/"):
            return target
        return None

    with app.app_context():
        init_db()
        ensure_default_admin()
        seed_existing_pages()

    @app.route("/")
    def index() -> str:
        return render_site_page("index.html", "home")

    @app.route("/about")
    def about() -> str:
        return render_site_page("about.html", "about")

    @app.route("/stem-pathways")
    def stem_pathways() -> str:
        return render_site_page("stem_pathways.html", "stem-pathways")

    @app.route("/study-options")
    def study_options() -> str:
        return render_site_page("study_options.html", "study-options")

    @app.route("/fees")
    def fees() -> str:
        return render_site_page("fees.html", "fees")

    @app.route("/how-we-teach")
    def how_we_teach() -> str:
        return render_site_page("how_we_teach.html", "how-we-teach")

    @app.route("/our-teacher-experts")
    def our_teacher_expert() -> str:
        return render_site_page("our_teacher_expert.html", "our-teacher-experts")

    @app.route("/informed-teaching")
    def informed_teaching() -> str:
        return render_site_page("informed_teaching.html", "informed-teaching")

    @app.route("/courses")
    def courses() -> str:
        return render_site_page("courses.html", "courses")

    @app.route("/course-details")
    def course_details() -> str:
        return render_site_page("course_details.html", "course-details")

    @app.route("/pricing")
    def pricing() -> str:
        return render_site_page("pricing.html", "pricing")

    @app.route("/blogs")
    def blogs() -> str:
        return render_site_page("blogs.html", "blogs")

    @app.route("/blog-details")
    def blog_details() -> str:
        return render_site_page("blog_details.html", "blog-details")

    @app.route("/reviews")
    def reviews() -> str:
        return render_site_page("reviews.html", "reviews")

    @app.route("/a-level-math")
    def a_level_math() -> str:
        return render_site_page("a_level_math.html", "a-level-math")

    @app.route("/our-mission")
    def our_mission() -> str:
        return render_site_page("our_mission.html", "our-mission")

    @app.route("/contact", methods=["GET", "POST"])
    def contact() -> str:
        form_data: dict[str, str] = {}
        if request.method == "POST":
            form_data = request.form.to_dict()
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip()
            phone = request.form.get("phone", "").strip()
            message = request.form.get("message", "").strip()
            source = request.form.get("source", request.path)

            if not full_name or not email:
                flash("Please provide your name and email so we can reach you.", "error")
            else:
                create_lead(
                    "contact",
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    message=message,
                    source=source,
                )
                flash("Thanks for reaching out — our admissions team will respond soon.", "success")
                return redirect(url_for("contact"))

        return render_site_page("contact.html", "contact", form_data=form_data)

    @app.route("/development")
    def development() -> str:
        return render_site_page("development.html", "development")

    @app.route("/under-development/<slug>")
    def placeholder_page(slug: str) -> str:
        return redirect(url_for("development"))

    @app.route("/policies")
    def policies_page() -> str:
        policies = fetch_all_policies()
        return render_site_page("policies.html", "policies", policies=policies)

    @app.route("/subscribe", methods=["POST"])
    def subscribe() -> str:
        email = request.form.get("email", "").strip()
        source = request.form.get("source") or request.referrer or "Website"
        if not email:
            flash("Please enter an email address to subscribe.", "error")
            return redirect(request.referrer or url_for("index"))

        create_lead("subscription", email=email, source=source)
        flash("Thanks for subscribing — we will keep you updated.", "success")
        return redirect(request.referrer or url_for("index"))

    @app.route("/admin/login", methods=["GET", "POST"])
    def admin_login() -> str:
        if session.get("user_id"):
            return redirect(url_for("admin_dashboard"))

        next_url = request.args.get("next")
        if request.method == "POST":
            username = request.form.get("username", "").strip().lower()
            password = request.form.get("password", "")

            if not username or not password:
                flash("Enter both username and password.", "error")
            else:
                db = get_db()
                user = db.execute(
                    "SELECT * FROM users WHERE username = ?", (username,)
                ).fetchone()
                if user and check_password_hash(user["password_hash"], password):
                    session["user_id"] = user["id"]
                    session["username"] = user["username"]
                    flash("Welcome back!", "success")
                    redirect_target = safe_next(next_url) or url_for("admin_dashboard")
                    return redirect(redirect_target)
                flash("Invalid credentials. Please try again.", "error")

        return render_template("admin/login.html")

    @app.route("/admin/logout")
    @login_required
    def admin_logout() -> str:
        session.clear()
        flash("You have been signed out.", "info")
        return redirect(url_for("admin_login"))

    @app.route("/admin")
    @login_required
    def admin_dashboard() -> str:
        db = get_db()
        leads = fetch_all_leads()

        total_leads = db.execute("SELECT COUNT(*) AS total FROM leads").fetchone()["total"]
        weekly_leads = db.execute(
            "SELECT COUNT(*) AS total FROM leads WHERE datetime(created_at) >= datetime('now', '-7 day')"
        ).fetchone()["total"]
        status_rows = db.execute(
            "SELECT status, COUNT(*) AS total FROM leads GROUP BY status"
        ).fetchall()
        status_counts = {row["status"]: row["total"] for row in status_rows}
        contact_count = db.execute(
            "SELECT COUNT(*) AS total FROM leads WHERE lead_type = ?",
            ("contact",),
        ).fetchone()["total"]
        subscription_count = db.execute(
            "SELECT COUNT(*) AS total FROM leads WHERE lead_type = ?",
            ("subscription",),
        ).fetchone()["total"]
        converted_count = sum(status_counts.get(key, 0) for key in ("Qualified", "Closed"))
        conversion_rate = round((converted_count / total_leads) * 100, 1) if total_leads else 0.0

        last_seven_days = [
            (datetime.utcnow() - timedelta(days=offset)).strftime("%Y-%m-%d")
            for offset in range(6, -1, -1)
        ]
        trend_rows = db.execute(
            """
            SELECT DATE(created_at) AS day, COUNT(*) AS total
            FROM leads
            WHERE datetime(created_at) >= datetime('now', '-6 day')
            GROUP BY DATE(created_at)
            ORDER BY DATE(created_at)
            """
        ).fetchall()
        trend_map = {row["day"]: row["total"] for row in trend_rows}

        trend_chart = {
            "labels": last_seven_days,
            "values": [trend_map.get(day, 0) for day in last_seven_days],
        }

        status_chart = {
            "labels": LEAD_STATUSES,
            "values": [status_counts.get(status, 0) for status in LEAD_STATUSES],
        }

        type_rows = db.execute(
            "SELECT lead_type, COUNT(*) AS total FROM leads GROUP BY lead_type"
        ).fetchall()
        type_counts = {row["lead_type"]: row["total"] for row in type_rows}
        type_chart = {
            "labels": list(type_counts.keys()),
            "values": list(type_counts.values()),
        }

        kpis = {
            "total_leads": total_leads,
            "weekly_leads": weekly_leads,
            "subscription_count": subscription_count,
            "contact_count": contact_count,
            "conversion_rate": conversion_rate,
        }

        recent_leads = leads[:10]

        return render_template(
            "admin/dashboard.html",
            statuses=LEAD_STATUSES,
            status_counts=status_counts,
            kpis=kpis,
            trend_chart=trend_chart,
            status_chart=status_chart,
            type_chart=type_chart,
            recent_leads=recent_leads,
        )

    @app.route("/admin/leads")
    @login_required
    def admin_leads() -> str:
        leads = fetch_all_leads()
        db = get_db()
        status_rows = db.execute(
            "SELECT status, COUNT(*) AS total FROM leads GROUP BY status"
        ).fetchall()
        status_counts = {row["status"]: row["total"] for row in status_rows}

        return render_template(
            "admin/leads.html",
            leads=leads,
            statuses=LEAD_STATUSES,
            status_counts=status_counts,
        )

    @app.route("/admin/pages")
    @login_required
    def admin_pages() -> str:
        pages = fetch_all_pages()
        parent_lookup = {page["id"]: page["page_name"] for page in pages}
        nav_counts: dict[str, int] = {"main": 0, "dropdown": 0, "footer": 0, "hidden": 0}
        meta_missing_ids: set[int] = set()

        for page in pages:
            display = page.get("nav_display") or "hidden"
            nav_counts[display] = nav_counts.get(display, 0) + 1
            if not page.get("seo_title") or not page.get("meta_description"):
                meta_missing_ids.add(page["id"])

        total_pages = len(pages)
        nav_visible = nav_counts.get("main", 0) + nav_counts.get("dropdown", 0)
        stats = {
            "total": total_pages,
            "meta_complete": total_pages - len(meta_missing_ids),
            "meta_missing": len(meta_missing_ids),
            "nav_counts": nav_counts,
            "nav_visible": nav_visible,
            "nav_footer": nav_counts.get("footer", 0),
        }

        return render_template(
            "admin/pages/index.html",
            pages=pages,
            parent_lookup=parent_lookup,
            nav_stats=stats,
            meta_gaps=meta_missing_ids,
        )

    @app.route("/admin/policies", methods=["GET", "POST"])
    @login_required
    def admin_policies() -> str:
        if request.method == "POST":
            document_file = request.files.get("document")
            thumbnail_file = request.files.get("thumbnail")
            title = request.form.get("title", "").strip()
            original_filename = document_file.filename if document_file else ""

            try:
                document_path = save_policy_document(document_file)
            except ValueError as exc:
                flash(str(exc), "error")
                return redirect(url_for("admin_policies"))

            if not title:
                title = guess_policy_title_from_filename(original_filename)

            try:
                thumbnail_path = save_policy_thumbnail(thumbnail_file)
            except ValueError as exc:
                remove_static_file(document_path)
                flash(str(exc), "error")
                return redirect(url_for("admin_policies"))

            create_policy_record(
                title=title,
                document_path=document_path,
                thumbnail_path=thumbnail_path,
            )
            flash("Policy uploaded successfully.", "success")
            return redirect(url_for("admin_policies"))

        policies = fetch_all_policies()
        return render_template("admin/policies.html", policies=policies)

    @app.post("/admin/policies/<int:policy_id>/delete")
    @login_required
    def admin_policies_delete(policy_id: int):
        policy = get_policy(policy_id)
        if policy is None:
            flash("Policy not found.", "error")
            return redirect(url_for("admin_policies"))

        remove_static_file(policy["document_path"])
        remove_static_file(policy["thumbnail_path"])

        db = get_db()
        db.execute("DELETE FROM policies WHERE id = ?", (policy_id,))
        db.commit()
        flash("Policy deleted.", "info")
        return redirect(url_for("admin_policies"))

    def build_nav_parent_choices(exclude_id: int | None = None) -> list[sqlite3.Row]:
        pages = fetch_all_pages()
        choices: list[sqlite3.Row] = []
        for page in pages:
            if exclude_id is not None and page["id"] == exclude_id:
                continue
            choices.append(page)
        return choices

    def parse_nav_values(form, *, exclude_id: int | None = None) -> tuple[str, int | None, int]:
        nav_display = form.get("nav_display", "hidden")
        if nav_display not in {"main", "dropdown", "footer", "hidden"}:
            nav_display = "hidden"

        nav_parent_id: int | None = None
        if nav_display == "dropdown":
            raw_parent = form.get("nav_parent_id")
            if raw_parent:
                try:
                    nav_parent_id = int(raw_parent)
                except ValueError:
                    nav_parent_id = None
        if exclude_id is not None and nav_parent_id == exclude_id:
            nav_parent_id = None

        nav_order = 0
        try:
            nav_order = int(form.get("nav_order", "0"))
        except ValueError:
            nav_order = 0

        return nav_display, nav_parent_id, nav_order

    def handle_social_image_upload(existing: str | None = None):
        remove_flag = request.form.get("remove_social_image") == "on"
        if remove_flag:
            if existing:
                old_path = Path(app.root_path) / "static" / existing
                try:
                    old_path.unlink(missing_ok=True)
                except OSError:
                    pass
            return None

        file = request.files.get("social_image")
        if file and file.filename:
            try:
                new_path = save_social_image(file)
                if existing:
                    old_path = Path(app.root_path) / "static" / existing
                    try:
                        old_path.unlink(missing_ok=True)
                    except OSError:
                        pass
                return new_path
            except ValueError as exc:
                flash(str(exc), "error")
        return existing

    def ensure_template(template_choice: str, slug: str) -> str:
        if template_choice and template_choice != "__auto__":
            return template_choice

        filename = f"{slug}.html"
        template_relative = f"pages/{filename}"
        template_path = Path(app.config["PAGES_TEMPLATE_DIR"]) / filename
        if not template_path.exists():
                        template_content = """{% extends 'base.html' %}

{% block title %}{{ page['seo_title'] or page['page_name'] or 'New Page' }}{% endblock %}

{% block content %}
    <section class="py-20">
        <div class="container mx-auto px-6">
            <h1 class="text-4xl font-bold text-slate-900">{{ page['page_name'] }}</h1>
            <p class="mt-4 text-slate-600">
                This page was auto-generated. Update the content in templates/pages/{{ page['slug'] }}.html.
            </p>
        </div>
    </section>
{% endblock %}
"""
                        template_path.write_text(template_content, encoding="utf-8")
        return template_relative

    @app.route("/admin/pages/new", methods=["GET", "POST"])
    @login_required
    def admin_pages_new() -> str:
        template_options = available_templates()
        parent_choices = build_nav_parent_choices()

        if request.method == "POST":
            page_name = request.form.get("page_name", "").strip()
            seo_title = request.form.get("seo_title", "").strip() or None
            meta_description = request.form.get("meta_description", "").strip() or None
            nav_display, nav_parent_id, nav_order = parse_nav_values(request.form)
            template_choice = request.form.get("template_name", "__auto__")

            if not page_name:
                flash("Page name is required.", "error")
                return render_template(
                    "admin/pages/form.html",
                    mode="create",
                    template_options=template_options,
                    parent_choices=parent_choices,
                    form_data=request.form,
                )

            base_slug = slugify(page_name)
            slug = generate_unique_slug(base_slug)

            social_image = handle_social_image_upload()

            template_name = ensure_template(template_choice, slug)

            page_id = upsert_page(
                page_id=None,
                slug=slug,
                page_name=page_name,
                seo_title=seo_title,
                meta_description=meta_description,
                nav_display=nav_display,
                nav_parent_id=nav_parent_id,
                nav_order=nav_order,
                social_image=social_image,
                template_name=template_name,
            )

            flash("Page created successfully.", "success")
            return redirect(url_for("admin_pages_edit", page_id=page_id))

        return render_template(
            "admin/pages/form.html",
            mode="create",
            template_options=template_options,
            parent_choices=parent_choices,
            form_data={},
        )

    @app.route("/admin/pages/<int:page_id>/edit", methods=["GET", "POST"])
    @login_required
    def admin_pages_edit(page_id: int) -> str:
        page = get_page_by_id(page_id)
        if page is None:
            flash("Page not found.", "error")
            return redirect(url_for("admin_pages"))

        template_options = available_templates()
        parent_choices = build_nav_parent_choices(exclude_id=page_id)

        if request.method == "POST":
            page_name = request.form.get("page_name", "").strip()
            seo_title = request.form.get("seo_title", "").strip() or None
            meta_description = request.form.get("meta_description", "").strip() or None
            nav_display, nav_parent_id, nav_order = parse_nav_values(
                request.form, exclude_id=page_id
            )
            template_choice = request.form.get("template_name", page["template_name"])

            if not page_name:
                flash("Page name is required.", "error")
                return render_template(
                    "admin/pages/form.html",
                    mode="edit",
                    page=page,
                    template_options=template_options,
                    parent_choices=parent_choices,
                    form_data=request.form,
                )

            social_image = handle_social_image_upload(existing=page["social_image"])
            template_name = ensure_template(template_choice, page["slug"])

            upsert_page(
                page_id=page_id,
                slug=page["slug"],
                page_name=page_name,
                seo_title=seo_title,
                meta_description=meta_description,
                nav_display=nav_display,
                nav_parent_id=nav_parent_id,
                nav_order=nav_order,
                social_image=social_image,
                template_name=template_name,
            )

            flash("Page updated successfully.", "success")
            return redirect(url_for("admin_pages_edit", page_id=page_id))

        return render_template(
            "admin/pages/form.html",
            mode="edit",
            page=page,
            template_options=template_options,
            parent_choices=parent_choices,
            form_data=dict(page),
        )

    @app.post("/admin/pages/<int:page_id>/delete")
    @login_required
    def admin_pages_delete(page_id: int):
        page = get_page_by_id(page_id)
        if page is None:
            flash("Page not found.", "error")
            return redirect(url_for("admin_pages"))

        db = get_db()
        template_name = page["template_name"]
        social_image = page["social_image"]

        if social_image:
            social_path = Path(app.root_path) / "static" / social_image
            try:
                social_path.unlink(missing_ok=True)
            except OSError:
                pass

        template_usage = db.execute(
            "SELECT COUNT(*) AS total FROM pages WHERE template_name = ? AND id != ?",
            (template_name, page_id),
        ).fetchone()["total"]

        db.execute("DELETE FROM pages WHERE id = ?", (page_id,))
        db.commit()

        if template_usage == 0 and template_name.startswith("pages/"):
            template_path = template_root / template_name
            try:
                template_path.unlink(missing_ok=True)
            except OSError:
                pass

        flash("Page removed.", "info")
        return redirect(url_for("admin_pages"))

    @app.post("/admin/leads/<int:lead_id>/status")
    @login_required
    def update_lead_status(lead_id: int):
        new_status = request.form.get("status", "")
        if new_status not in LEAD_STATUSES:
            flash("Please choose a valid status.", "error")
            return redirect(request.referrer or url_for("admin_dashboard"))

        update_lead_status_db(lead_id, new_status)
        flash("Lead status updated.", "success")
        return redirect(request.referrer or url_for("admin_dashboard"))

    @app.route("/pages/<slug>")
    def render_dynamic_page(slug: str):
        page = get_page_by_slug(slug)
        if page is None:
            flash("The requested page could not be found.", "error")
            return redirect(url_for("index"))

        page_dict = dict(page)
        template_name = page_dict["template_name"]

        return render_template(
            template_name,
            page=page_dict,
            page_meta=page_dict,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
