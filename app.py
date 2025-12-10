import hashlib
import json
import os
import re
import sqlite3
from collections.abc import Sequence
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote_plus, urlparse

import click
from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   send_from_directory, session, url_for)
from flask.typing import ResponseReturnValue
from flask_compress import Compress
from flask_mail import Mail, Message
from markupsafe import Markup, escape
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from scripts import process_images as process_images_module

LEAD_STATUSES = [
    "New",
    "Contacted",
    "In Progress",
    "Qualified",
    "Closed",
]

CONSULTATION_STATUSES = [
    "Pending",
    "Awaiting Confirmation",
    "Confirmed",
    "Rescheduled",
    "Completed",
    "Cancelled",
    "No Show",
]

CONSULTATION_TIME_SLOTS = (
    "09:00",
    "10:00",
    "11:00",
    "12:30",
    "14:00",
    "15:30",
    "17:00",
)

CONSULTATION_TIMEZONES: tuple[tuple[str, str], ...] = (
    ("Europe/London", "GMT/BST (London)"),
    ("Europe/Paris", "Central European Time"),
    ("Asia/Dubai", "Gulf Standard Time"),
    ("Asia/Singapore", "Singapore Standard Time"),
    ("Asia/Kuala_Lumpur", "Malaysia Time"),
    ("Asia/Hong_Kong", "Hong Kong Time"),
    ("America/New_York", "Eastern Time"),
    ("America/Los_Angeles", "Pacific Time"),
)

DEFAULT_PAGE_SEEDS: list[dict[str, str | int | None]] = [
    {
        "slug": "home",
        "page_name": "Homepage",
        "template_name": "index.html",
        "nav_order": 10,
        "nav_display": "hidden",
        "seo_title": "London Maths & Science College | Specialist STEM Sixth Form",
        "meta_description": (
            "Discover London Maths & Science College, a specialist 16-19 STEM sixth form in London "
            "offering A Levels, GCSEs and clear routes to top universities."
        ),
    },
    {
        "slug": "about",
        "page_name": "About LMSC",
        "template_name": "about.html",
        "nav_order": 20,
        "nav_display": "dropdown",
        "seo_title": "About London Maths & Science College | Who We Are",
        "meta_description": (
            "Learn about our mission, values and leadership at London Maths & Science College, the "
            "specialist STEM sixth form for ambitious 16-19 students."
        ),
    },
    {
        "slug": "stem-pathways",
        "page_name": "STEM Pathways",
        "template_name": "stem_pathways.html",
        "nav_order": 30,
        "nav_display": "dropdown",
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
        "nav_display": "dropdown",
        "seo_title": "Study Options | Learn Online or On Campus with LMSC",
        "meta_description": (
            "See the flexible study options at LMSC, combining online lessons and in-person teaching so "
            "every student can access the STEM programme that fits their life."
        ),
    },
    {
        "slug": "prospectus",
        "page_name": "Prospectus",
        "template_name": "prospectus.html",
        "nav_order": 45,
        "nav_display": "dropdown",
        "seo_title": "Download the LMSC Prospectus | STEM Sixth Form",
        "meta_description": (
            "Browse the London Maths & Science College prospectus, explore specialist STEM pathways and "
            "download the latest edition for admissions guidance."
        ),
    },
    {
        "slug": "fees",
        "page_name": "Fees & Finance",
        "template_name": "fees.html",
        "nav_order": 50,
        "nav_display": "dropdown",
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
        "nav_display": "dropdown",
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
        "nav_display": "dropdown",
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
        "nav_display": "dropdown",
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
        "slug": "book-a-consultation",
        "page_name": "Book a Consultation",
        "template_name": "book_consultation.html",
        "nav_order": 115,
        "nav_display": "main",
        "seo_title": "Book a Consultation | London Maths & Science College",
        "meta_description": (
            "Choose a time to speak with the London Maths & Science College admissions team about A Level "
            "and GCSE STEM pathways, scholarships and study formats."
        ),
    },
    {
        "slug": "blogs",
        "page_name": "Blogs",
        "template_name": "blogs.html",
        "nav_order": 120,
        "nav_display": "dropdown",
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
        "nav_display": "dropdown",
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
        "nav_display": "main",
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
    {
        "slug": "open-events",
        "page_name": "Open Events",
        "template_name": "development.html",
        "nav_order": 200,
        "nav_display": "dropdown",
        "seo_title": "Open Events | London Maths & Science College",
        "meta_description": (
            "Discover upcoming open days, meet-the-team evenings and campus tours at London Maths & Science College."
        ),
    },
    {
        "slug": "support-send-learners",
        "page_name": "Support for SEND Learners",
        "template_name": "development.html",
        "nav_order": 210,
        "nav_display": "dropdown",
        "seo_title": "SEND Support | London Maths & Science College",
        "meta_description": (
            "Learn how LMSC supports students with special educational needs and disabilities through tailored provision."
        ),
    },
    {
        "slug": "digital-learning-devices",
        "page_name": "Digital Learning & Devices",
        "template_name": "development.html",
        "nav_order": 220,
        "nav_display": "dropdown",
        "seo_title": "Digital Learning & Devices | LMSC",
        "meta_description": (
            "Review device guidance, connectivity requirements and the digital platforms used by LMSC learners."
        ),
    },
    {
        "slug": "academic-facilities-labs",
        "page_name": "Academic Facilities & Labs",
        "template_name": "development.html",
        "nav_order": 230,
        "nav_display": "dropdown",
        "seo_title": "Academic Facilities & Labs | LMSC",
        "meta_description": (
            "Explore the specialist laboratories, classrooms and learning spaces available to LMSC students."
        ),
    },
    {
        "slug": "life-at-lmsc",
        "page_name": "Life at LMSC",
        "template_name": "development.html",
        "nav_order": 240,
        "nav_display": "dropdown",
        "seo_title": "Life at LMSC | London Maths & Science College",
        "meta_description": (
            "Get a feel for daily life, culture and community at London Maths & Science College."
        ),
    },
    {
        "slug": "student-community",
        "page_name": "Our Student Community",
        "template_name": "development.html",
        "nav_order": 250,
        "nav_display": "dropdown",
        "seo_title": "Student Community | London Maths & Science College",
        "meta_description": (
            "Meet the diverse student community at LMSC and learn how we celebrate every learner."
        ),
    },
    {
        "slug": "pastoral-care-wellbeing",
        "page_name": "Pastoral Care & Wellbeing",
        "template_name": "development.html",
        "nav_order": 260,
        "nav_display": "dropdown",
        "seo_title": "Pastoral Care & Wellbeing | LMSC",
        "meta_description": (
            "See how LMSC supports student wellbeing through pastoral programmes and mentoring."
        ),
    },
    {
        "slug": "tutor-system-mentoring",
        "page_name": "Tutor System & Mentoring",
        "template_name": "development.html",
        "nav_order": 270,
        "nav_display": "dropdown",
        "seo_title": "Tutor System & Mentoring | LMSC",
        "meta_description": (
            "Understand the tutor system and mentoring pathways that guide every learner at LMSC."
        ),
    },
    {
        "slug": "inclusion-student-voice",
        "page_name": "Inclusion & Student Voice",
        "template_name": "development.html",
        "nav_order": 280,
        "nav_display": "dropdown",
        "seo_title": "Inclusion & Student Voice | LMSC",
        "meta_description": (
            "Learn how students influence college life through councils, feedback forums and inclusive initiatives."
        ),
    },
    {
        "slug": "sphere-programme",
        "page_name": "SPHERE Programme",
        "template_name": "development.html",
        "nav_order": 290,
        "nav_display": "dropdown",
        "seo_title": "SPHERE Programme | LMSC",
        "meta_description": (
            "Discover the SPHERE enrichment programme that broadens horizons beyond the core curriculum."
        ),
    },
    {
        "slug": "faith-religious-provision",
        "page_name": "Faith & Religious Provision",
        "template_name": "development.html",
        "nav_order": 300,
        "nav_display": "dropdown",
        "seo_title": "Faith & Religious Provision | LMSC",
        "meta_description": (
            "Explore how LMSC accommodates faith observance, prayer spaces and cultural celebrations."
        ),
    },
    {
        "slug": "assemblies-events",
        "page_name": "Assemblies & Events",
        "template_name": "development.html",
        "nav_order": 310,
        "nav_display": "dropdown",
        "seo_title": "Assemblies & Events | London Maths & Science College",
        "meta_description": (
            "Stay informed about assemblies, guest speakers and signature events at LMSC."
        ),
    },
    {
        "slug": "summer-camps-enrichment",
        "page_name": "Summer Camps & Enrichment",
        "template_name": "development.html",
        "nav_order": 320,
        "nav_display": "dropdown",
        "seo_title": "Summer Camps & Enrichment | LMSC",
        "meta_description": (
            "Review summer schools, enrichment camps and holiday programmes offered by LMSC."
        ),
    },
    {
        "slug": "online-homeschooling-programmes",
        "page_name": "Online Homeschooling Programmes",
        "template_name": "development.html",
        "nav_order": 330,
        "nav_display": "dropdown",
        "seo_title": "Online Homeschooling Programmes | LMSC",
        "meta_description": (
            "Discover flexible online and homeschooling programmes delivered by LMSC tutors."
        ),
    },
    {
        "slug": "homeschooling-advice-support",
        "page_name": "Homeschooling Advice & Support",
        "template_name": "development.html",
        "nav_order": 340,
        "nav_display": "dropdown",
        "seo_title": "Homeschooling Advice & Support | LMSC",
        "meta_description": (
            "Access guidance, toolkits and helplines for families undertaking homeschooling with LMSC."
        ),
    },
    {
        "slug": "computer-requirements",
        "page_name": "Computer Requirements",
        "template_name": "development.html",
        "nav_order": 350,
        "nav_display": "dropdown",
        "seo_title": "Computer Requirements | LMSC",
        "meta_description": (
            "Check recommended hardware and software specifications for successful online study at LMSC."
        ),
    },
    {
        "slug": "it-helpdesk-support",
        "page_name": "IT Helpdesk & Support",
        "template_name": "development.html",
        "nav_order": 360,
        "nav_display": "dropdown",
        "seo_title": "IT Helpdesk & Support | LMSC",
        "meta_description": (
            "Find out how to reach the LMSC IT helpdesk for technical support and troubleshooting."
        ),
    },
    {
        "slug": "student-parent-faqs",
        "page_name": "Student & Parent FAQs",
        "template_name": "development.html",
        "nav_order": 370,
        "nav_display": "dropdown",
        "seo_title": "Student & Parent FAQs | LMSC",
        "meta_description": (
            "Browse answers to frequently asked questions from students and parents about LMSC."
        ),
    },
    {
        "slug": "university-careers-guidance",
        "page_name": "University & Careers Guidance",
        "template_name": "development.html",
        "nav_order": 380,
        "nav_display": "dropdown",
        "seo_title": "University & Careers Guidance | LMSC",
        "meta_description": (
            "See how LMSC provides careers coaching, UCAS support and destination planning for every learner."
        ),
    },
    {
        "slug": "study-guidance",
        "page_name": "Study Guidance",
        "template_name": "development.html",
        "nav_order": 390,
        "nav_display": "dropdown",
        "seo_title": "Study Guidance | London Maths & Science College",
        "meta_description": (
            "Unlock study strategies, revision techniques and subject guidance curated by LMSC teachers."
        ),
    },
    {
        "slug": "exam-information-policies",
        "page_name": "Exam Information & Policies",
        "template_name": "development.html",
        "nav_order": 400,
        "nav_display": "dropdown",
        "seo_title": "Exam Information & Policies | LMSC",
        "meta_description": (
            "Find exam timetables, regulations and guidance notes for assessments at LMSC."
        ),
    },
    {
        "slug": "strategy-vision",
        "page_name": "Strategy & Vision",
        "template_name": "development.html",
        "nav_order": 410,
        "nav_display": "dropdown",
        "seo_title": "Strategy & Vision | London Maths & Science College",
        "meta_description": (
            "Read about the college strategy, long-term vision and development priorities at LMSC."
        ),
    },
    {
        "slug": "meet-the-principal",
        "page_name": "Meet the Principal",
        "template_name": "development.html",
        "nav_order": 420,
        "nav_display": "dropdown",
        "seo_title": "Meet the Principal | London Maths & Science College",
        "meta_description": (
            "Hear from the Principal of LMSC about our ethos, ambitions and student successes."
        ),
    },
    {
        "slug": "leadership-governance",
        "page_name": "Leadership & Governance",
        "template_name": "development.html",
        "nav_order": 430,
        "nav_display": "dropdown",
        "seo_title": "Leadership & Governance | LMSC",
        "meta_description": (
            "Meet the leadership team and governance partners who steward London Maths & Science College."
        ),
    },
    {
        "slug": "partnerships-outreach",
        "page_name": "Partnerships & Outreach",
        "template_name": "development.html",
        "nav_order": 440,
        "nav_display": "dropdown",
        "seo_title": "Partnerships & Outreach | London Maths & Science College",
        "meta_description": (
            "Discover outreach projects, employer links and partnerships that enrich learning at LMSC."
        ),
    },
]

DEFAULT_COURSE_SEED: list[dict[str, Any]] = [
    {
        "slug": "mastering-ui-ux-design",
        "level": "UI/UX Design",
        "title": "Mastering UI/UX design from fundamentals to advanced",
        "image_path": "Images/Image 1.jpg",
        "image_alt": "Student analysing UI wireframes",
        "short_description": "Starting with the core principles of design, the course delves into research, prototyping and interaction at scale.",
        "hours": 120,
        "display_order": 10,
        "about_course": (
            "Creative learners join a structured pathway that explores discovery research, interaction principles and "
            "production-ready interface systems. Lessons blend case studies with guided briefs so every concept is grounded "
            "in practice."
        ),
        "study_topics": "Research synthesis and persona building\nDesign system foundations\nPrototyping and usability testing",
        "skills_built": "Advanced Figma workflows\nAccessibility-first design\nStakeholder presentation",
        "audience_notes": "A Level students targeting design degrees\nSTEM learners adding creative portfolios\nCareer switchers seeking UX credentials",
        "exam_details": (
            "Internal studio assessments mirror Edexcel-style coursework with two moderated design sprints each term. "
            "Learners submit a digital portfolio in May ahead of the viva-style presentation in June."
        ),
        "entry_requirements": (
            "GCSE English Language at grade 5 or above, GCSE Maths at grade 5 or above, and a short creative portfolio "
            "review completed during consultation."
        ),
        "course_outcome": (
            "Graduates compile a refined UX/UI portfolio with research artefacts, interactive prototypes and reflective case "
            "studies suitable for university admissions."
        ),
        "progression": (
            "Typical offers include interaction design, human-computer interaction and digital product design degrees at "
            "Russell Group and art-focused universities."
        ),
        "sidebar_fees": "From £4,950 per term",
        "sidebar_summary": "Hybrid delivery with studio critiques, live briefs and one-to-one portfolio coaching.",
        "includes_items": "Weekly mentor feedback\nIndustry-standard tooling licenses\nCurated reading lists",
        "custom_content": (
            "<h3>Inside the studio</h3>\n"
            "<p>Weekly labs translate research insights into production-ready interface systems with senior mentor feedback.</p>\n"
            "<ul>\n"
            "<li>Design clinics with portfolio critiques</li>\n"
            "<li>Guided usability testing playbooks</li>\n"
            "<li>Access to curated case study archive</li>\n"
            "</ul>"
        ),
    },
    {
        "slug": "creative-web-design",
        "level": "Web Design",
        "title": "Creative Web Design: Crafting visually stunning experiences",
        "image_path": "Images/Image 2.jpg",
        "image_alt": "Web designer working across multiple screens",
        "short_description": "Explore responsive layouts, motion and accessibility as you build a professional portfolio from day one.",
        "hours": 110,
        "display_order": 20,
        "about_course": (
            "Learners master visual storytelling across responsive screens, combining typography, colour theory and motion "
            "principles with modern front-end collaboration rituals."
        ),
        "study_topics": "Atomic design systems\nAdvanced layout composition\nMicro-interactions and motion",
        "skills_built": "High-fidelity prototyping\nDesign to developer handoff\nAccessibility auditing",
        "audience_notes": "Students building creative portfolios\nAspiring product designers\nDevelopers refining visual craft",
        "exam_details": (
            "Capstone projects are assessed through annotated prototypes, paired user testing and reflective journals, all "
            "moderated during the final studio showcase."
        ),
        "entry_requirements": (
            "GCSE English at grade 5, GCSE Art or Design Technology recommended, and completion of a creative task set by "
            "the admissions tutor."
        ),
        "course_outcome": (
            "Students graduate with a polished responsive design system, interaction guidelines and documented user insights."
        ),
        "progression": (
            "Progress to degrees in digital media, experience design, creative computing and related studio apprenticeships."
        ),
        "sidebar_fees": "From £4,650 per term",
        "sidebar_summary": "Studio-led delivery with critique panels and collaborative sprints held each half term.",
        "includes_items": "Showcase events with industry guests\nPortfolio-ready component library\n24/7 resource hub access",
        "custom_content": (
            "<h3>Project delivery</h3>\n"
            "<p>Studio briefs balance creative direction with responsive build considerations, so every learner ships polished prototypes.</p>\n"
            "<ul>\n"
            "<li>Weekly motion and interaction labs</li>\n"
            "<li>Crit panels featuring guest designers</li>\n"
            "<li>Component library handoff templates</li>\n"
            "</ul>"
        ),
    },
    {
        "slug": "mastering-web-development",
        "level": "Web Development",
        "title": "Mastering web development from fundamentals to advanced builds",
        "image_path": "Images/Image 3.jpg",
        "image_alt": "Developer reviewing code snippets on a laptop",
        "short_description": "Learn to architect full-stack applications with modern tooling, deployment and performance optimisation.",
        "hours": 140,
        "display_order": 30,
        "about_course": (
            "This intensive pathway covers modern JavaScript frameworks, backend APIs and DevOps pipelines so learners can "
            "ship production-ready products with confidence."
        ),
        "study_topics": "API design and integration\nComponent-driven architectures\nTesting and deployment automation",
        "skills_built": "Full-stack project delivery\nVersion control collaboration\nPerformance monitoring",
        "audience_notes": "A Level Computer Science cohort\nSTEM learners targeting software engineering\nEntrepreneurs building MVPs",
        "exam_details": (
            "Learners complete three build cycles culminating in an assessed full-stack project with written technical "
            "documentation and viva demonstration."
        ),
        "entry_requirements": (
            "GCSE Maths at grade 6 or above and evidence of prior programming study, plus a technical challenge completed "
            "during admissions."
        ),
        "course_outcome": (
            "Graduates submit a Git-based portfolio with automated test suites, deployment workflows and analytics dashboards."
        ),
        "progression": (
            "Alumni progress to computer science, software engineering, data science and degree apprenticeships with tech firms."
        ),
        "sidebar_fees": "From £5,200 per term",
        "sidebar_summary": "Project-based delivery anchored by agile rituals and senior engineer mentorship.",
        "includes_items": "Cloud sandbox environments\nWeekly code reviews\nInterview preparation labs",
        "custom_content": (
            "<h3>Engineering practice</h3>\n"
            "<p>Sprint-based build cycles reinforce testing, deployment and observability so learners grow production instincts.</p>\n"
            "<ul>\n"
            "<li>Live CI/CD demonstrations</li>\n"
            "<li>Paired architecture whiteboard sessions</li>\n"
            "<li>Performance tuning clinics</li>\n"
            "</ul>"
        ),
    },
    {
        "slug": "digital-marketing-mastery",
        "level": "Digital Marketing",
        "title": "Digital marketing mastery: strategies for success online",
        "image_path": "Images/Image 5.jpg",
        "image_alt": "Marketing specialist presenting growth charts",
        "short_description": "Unlock data-driven acquisition, content strategy and paid media tactics with guided mentor support.",
        "hours": 100,
        "display_order": 40,
        "about_course": (
            "Learners engineer full-funnel marketing campaigns, balancing creative storytelling with rigorous analytics "
            "and budget optimisation techniques."
        ),
        "study_topics": "Audience segmentation\nPaid media optimisation\nLifecycle email automation",
        "skills_built": "Campaign planning\nData storytelling\nStakeholder reporting",
        "audience_notes": "Students targeting business and marketing degrees\nFounders scaling start-ups\nCareer changers entering growth roles",
        "exam_details": (
            "Assessment blends live campaign audits, scenario-based strategy decks and a final marketing operations playbook."
        ),
        "entry_requirements": (
            "GCSE English at grade 5, GCSE Maths at grade 5 and evidence of interest in marketing or communications."
        ),
        "course_outcome": (
            "Graduates deliver a multi-channel campaign suite with dashboards, creative messaging and optimisation roadmap."
        ),
        "progression": (
            "Students progress to marketing, business management, communications and digital media degree programmes."
        ),
        "sidebar_fees": "From £4,300 per term",
        "sidebar_summary": "Live briefs with real businesses plus analytics labs that simulate agency environments.",
        "includes_items": "Certifications in Google Analytics\nCopywriting workshops\nAccess to paid media simulators",
        "custom_content": (
            "<h3>Campaign labs</h3>\n"
            "<p>Teams iterate on real client briefs, balancing creative messaging with data-driven optimisation and reporting.</p>\n"
            "<ul>\n"
            "<li>Funnel diagnostics with dashboards</li>\n"
            "<li>Content strategy stand-ups</li>\n"
            "<li>Measurement frameworks for stakeholders</li>\n"
            "</ul>"
        ),
    },
    {
        "slug": "app-development-innovation",
        "level": "Apps Development",
        "title": "App development: building innovative mobile solutions",
        "image_path": "Images/Image 7.jpg",
        "image_alt": "Mobile developer testing an application prototype",
        "short_description": "Create high-performance native and cross-platform apps backed by real-world product case studies.",
        "hours": 130,
        "display_order": 50,
        "about_course": (
            "Combining product strategy with engineering execution, this pathway guides learners through native iOS, Android "
            "and cross-platform builds with iterative user testing."
        ),
        "study_topics": "Mobile UX patterns\nNative and cross-platform stacks\nApp store deployment",
        "skills_built": "Feature roadmap planning\nMobile performance tuning\nUser analytics instrumentation",
        "audience_notes": "Developers targeting mobile specialisms\nSTEM learners preparing for software apprenticeships\nFounders validating app concepts",
        "exam_details": (
            "Final assessment pairs a technical build review with a product pitch, covering architecture choices, adoption "
            "metrics and monetisation plans."
        ),
        "entry_requirements": (
            "GCSE Maths at grade 6, evidence of programming experience and portfolio discussion during admissions interview."
        ),
        "course_outcome": (
            "Students release a beta-ready application with analytics instrumentation, backlog management and release notes."
        ),
        "progression": (
            "Common destinations include software engineering, computer science and digital product innovation degrees."
        ),
        "sidebar_fees": "From £5,000 per term",
        "sidebar_summary": "Hands-on labs with device testing, beta programmes and investor pitch rehearsals.",
        "includes_items": "Device lab access\nProduct coaching clinics\nBeta tester recruitment support",
        "custom_content": (
            "<h3>Prototype pipeline</h3>\n"
            "<p>Learners scale app concepts from discovery to deployment using device labs, instrumentation and user testing.</p>\n"
            "<ul>\n"
            "<li>Sprint retros with product mentors</li>\n"
            "<li>App store readiness reviews</li>\n"
            "<li>Analytics instrumentation walkthroughs</li>\n"
            "</ul>"
        ),
    },
    {
        "slug": "ui-ux-design-experience",
        "level": "UI/UX Design",
        "title": "UI/UX design: crafting engaging user experiences",
        "image_path": "Images/Image 8.jpg",
        "image_alt": "Student shaping interface flows on a whiteboard",
        "short_description": "Master interaction design, design systems and analytics to measure how learners engage with your products.",
        "hours": 115,
        "display_order": 60,
        "about_course": (
            "Learners focus on advanced service design, research operations and experimentation frameworks that underpin "
            "data-informed customer experiences."
        ),
        "study_topics": "Service blueprints\nExperiment design\nDesign analytics dashboards",
        "skills_built": "Facilitating co-creation workshops\nDesign ops tooling\nConversion rate experimentation",
        "audience_notes": "Experience designers seeking progression\nProduct strategists broadening skillsets\nAnalytical creatives",
        "exam_details": (
            "Assessment includes a service design capstone, experimentation plan and stakeholder playback with cross-functional feedback."
        ),
        "entry_requirements": (
            "Interview portfolio review plus prior study in design, computing or aligned subjects at GCSE or AS Level."
        ),
        "course_outcome": (
            "Participants produce a service blueprint, experimentation roadmap and impact dashboard aligned to university expectations."
        ),
        "progression": (
            "Progress to human-centred design, innovation management and digital product leadership degrees."
        ),
        "sidebar_fees": "From £4,950 per term",
        "sidebar_summary": "Project clinics with senior mentors, experimentation labs and university application coaching.",
        "includes_items": "University portfolio reviews\nExperimentation toolkit\nAccess to alumni mentoring network",
        "custom_content": (
            "<h3>Experience design deep dives</h3>\n"
            "<p>Workshops apply experimentation frameworks to real service journeys, supported by analytics and storytelling labs.</p>\n"
            "<ul>\n"
            "<li>Service blueprint facilitation practice</li>\n"
            "<li>Experiment design playbooks</li>\n"
            "<li>Stakeholder storytelling clinics</li>\n"
            "</ul>"
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
    "prospectus": "prospectus",
    "fees": "fees",
    "how-we-teach": "how_we_teach",
    "our-teacher-experts": "our_teacher_expert",
    "informed-teaching": "informed_teaching",
    "courses": "courses",
    "course-details": "course_details",
    "pricing": "pricing",
    "book-a-consultation": "book_consultation",
    "blogs": "blogs",
    "blog-details": "blog_details",
    "reviews": "reviews",
    "a-level-math": "a_level_math",
    "our-mission": "our_mission",
    "contact": "contact",
    "development": "development",
    "policies": "policies_page",
}

NOINDEX_SLUGS: frozenset[str] = frozenset(
    {
        "thank-you",
        "subscribe-confirmed",
        "form-success",
        "development",
    }
)

SOCIAL_DOMAINS = (
    "facebook.com",
    "instagram.com",
    "twitter.com",
    "t.co",
    "linkedin.com",
    "youtube.com",
    "tiktok.com",
    "snapchat.com",
    "pinterest.com",
)

SEARCH_DOMAINS = (
    "google.",
    "bing.",
    "yahoo.",
    "duckduckgo.",
    "baidu.",
    "yandex.",
    "ask.com",
    "ecosia.org",
)


BLOG_IMAGE_FIELD_MAP: dict[str, tuple[str, str, str]] = {
    "thumbnail": ("thumbnail_path", "thumbnail_alt", "thumbnail"),
    "cover_image": ("cover_image_path", "cover_image_alt", "cover"),
    "picture_one": ("picture_one_path", "picture_one_alt", "picture one"),
    "picture_two": ("picture_two_path", "picture_two_alt", "picture two"),
    "picture_three": ("picture_three_path", "picture_three_alt", "picture three"),
}

BLOG_RELATION_FIELDS: tuple[str, ...] = (
    "related_article_1_slug",
    "related_article_2_slug",
    "related_article_3_slug",
)

BLOG_DB_COLUMNS: tuple[str, ...] = (
    "slug",
    "title",
    "publish_date",
    "summary",
    "thumbnail_path",
    "thumbnail_alt",
    "cover_image_path",
    "cover_image_alt",
    "heading_one",
    "text_content_one",
    "picture_one_path",
    "picture_one_alt",
    "heading_two",
    "text_content_two",
    "quote_block",
    "heading_three",
    "picture_two_path",
    "picture_two_alt",
    "heading_four",
    "text_content_three",
    "picture_three_path",
    "picture_three_alt",
    "text_content_four",
    "related_article_1_slug",
    "related_article_2_slug",
    "related_article_3_slug",
)
COURSE_DB_COLUMNS: tuple[str, ...] = (
    "slug",
    "level",
    "title",
    "image_path",
    "image_alt",
    "short_description",
    "hours",
    "display_order",
    "about_course",
    "study_topics",
    "skills_built",
    "audience_notes",
    "exam_details",
    "entry_requirements",
    "course_outcome",
    "progression",
    "sidebar_fees",
    "sidebar_summary",
    "includes_items",
    "custom_content",
    "related_course_1_slug",
    "related_course_2_slug",
    "related_course_3_slug",
)

COURSE_MULTILINE_FIELDS: tuple[str, ...] = (
    "includes_items",
)

COURSE_TEXT_BLOCK_FIELDS: tuple[str, ...] = (
    "about_course",
    "study_topics",
    "skills_built",
    "audience_notes",
    "exam_details",
    "entry_requirements",
    "course_outcome",
    "progression",
    "sidebar_summary",
)

COURSE_RELATION_FIELDS: tuple[str, ...] = (
    "related_course_1_slug",
    "related_course_2_slug",
    "related_course_3_slug",
)

COURSE_SCHEMA_ADDITIONAL_COLUMNS: dict[str, str] = {
    "slug": "TEXT",
    "about_course": "TEXT",
    "study_topics": "TEXT",
    "skills_built": "TEXT",
    "audience_notes": "TEXT",
    "exam_details": "TEXT",
    "entry_requirements": "TEXT",
    "course_outcome": "TEXT",
    "progression": "TEXT",
    "sidebar_fees": "TEXT",
    "sidebar_summary": "TEXT",
    "includes_items": "TEXT",
    "custom_content": "TEXT",
    "related_course_1_slug": "TEXT",
    "related_course_2_slug": "TEXT",
    "related_course_3_slug": "TEXT",
}

CAROUSEL_DB_COLUMNS: tuple[str, ...] = (
    "headline",
    "headline_highlights",
    "body",
    "cta_label",
    "cta_url",
    "image_path",
    "image_alt",
    "display_order",
    "is_active",
)

DEFAULT_CAROUSEL_SLIDES: list[dict[str, Any]] = [
    {
        "headline": "British 16-19 STEM College in London",
        "headline_highlights": "STEM College\nLondon",
        "body": (
            "London Maths & Science College (LMSC) is a British sixth form college based in London, "
            "specialising in A Levels and BTECs in Maths, Sciences, Computing and Business. Ambitious "
            "students from the UK and overseas study in small classes with rigorous teaching and clear expectations."
        ),
        "cta_label": "Explore our courses",
        "cta_url": "/courses",
        "image_path": "Images/Image 1.jpg",
        "image_alt": "Students studying together",
        "display_order": 1,
        "is_active": 1,
    },
    {
        "headline": "Study the Full British Curriculum from Anywhere",
        "headline_highlights": "British Curriculum\nAnywhere",
        "body": (
            "Follow the same British curriculum studied in leading UK schools, taught from London by specialist teachers. "
            "LMSC prepares students worldwide for British A Levels and BTEC qualifications recognised by universities across the UK and beyond."
        ),
        "cta_label": "Learn about the British curriculum",
        "cta_url": "/stem-pathways",
        "image_path": "Images/Image 2.jpg",
        "image_alt": "Students attending an online lesson",
        "display_order": 2,
        "is_active": 1,
    },
    {
        "headline": "In-Person, Online or Hybrid - You Choose",
        "headline_highlights": "Online or Hybrid",
        "body": (
            "Study on campus in London, fully online, or through a flexible hybrid route. Whichever study mode you choose, "
            "you follow the same British curriculum, timetable structure and assessment, with live lessons and full lesson recordings."
        ),
        "cta_label": "Compare study modes",
        "cta_url": "/study-options",
        "image_path": "Images/Image 3.jpg",
        "image_alt": "Students collaborating during a lesson",
        "display_order": 3,
        "is_active": 1,
    },
]


mail = Mail()
compress = Compress()


def create_app() -> Flask:
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)  # type: ignore[assignment]
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret")
    app.config.setdefault("PREFERRED_URL_SCHEME", "https")
    app.config.setdefault(
        "ENABLE_HTTPS_REDIRECT",
        os.environ.get("ENABLE_HTTPS_REDIRECT", "1") == "1",
    )

    app.config.setdefault("COMPRESS_ALGORITHM", "gzip")
    app.config.setdefault("COMPRESS_ALGORITHMS", ["gzip", "br"])
    app.config.setdefault("COMPRESS_BR_LEVEL", 5)
    app.config.setdefault("COMPRESS_LEVEL", 6)
    app.config.setdefault("COMPRESS_MIN_SIZE", 512)

    try:
        static_cache_seconds = int(os.environ.get("STATIC_CACHE_SECONDS", str(60 * 60 * 24 * 30)))
    except ValueError:
        static_cache_seconds = 60 * 60 * 24 * 30
    app.config.setdefault("STATIC_CACHE_SECONDS", static_cache_seconds)
    app.config.setdefault("SEND_FILE_MAX_AGE_DEFAULT", static_cache_seconds)
    app.config.setdefault(
        "SEED_DEFAULT_COURSES",
        os.environ.get("SEED_DEFAULT_COURSES", "1") == "1",
    )

    template_root = Path(app.root_path) / "templates"
    pages_template_dir = template_root / "pages"
    pages_template_dir.mkdir(parents=True, exist_ok=True)
    app.config["PAGES_TEMPLATE_DIR"] = str(pages_template_dir)

    uploads_dir = Path(app.root_path) / "static" / "uploads" / "social"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.config["SOCIAL_IMAGE_UPLOAD_FOLDER"] = str(uploads_dir)

    blog_images_dir = Path(app.root_path) / "static" / "uploads" / "blogs"
    blog_images_dir.mkdir(parents=True, exist_ok=True)
    app.config["BLOG_IMAGE_UPLOAD_FOLDER"] = str(blog_images_dir)

    course_images_dir = Path(app.root_path) / "static" / "uploads" / "courses"
    course_images_dir.mkdir(parents=True, exist_ok=True)
    app.config["COURSE_IMAGE_UPLOAD_FOLDER"] = str(course_images_dir)

    carousel_images_dir = Path(app.root_path) / "static" / "uploads" / "carousel"
    carousel_images_dir.mkdir(parents=True, exist_ok=True)
    app.config["CAROUSEL_IMAGE_UPLOAD_FOLDER"] = str(carousel_images_dir)

    policy_docs_dir = Path(app.root_path) / "static" / "uploads" / "policies" / "documents"
    policy_thumbs_dir = Path(app.root_path) / "static" / "uploads" / "policies" / "thumbnails"
    policy_docs_dir.mkdir(parents=True, exist_ok=True)
    policy_thumbs_dir.mkdir(parents=True, exist_ok=True)

    app.config["POLICY_DOC_UPLOAD_FOLDER"] = str(policy_docs_dir)
    app.config["POLICY_THUMB_UPLOAD_FOLDER"] = str(policy_thumbs_dir)

    prospectus_dir = Path(app.root_path) / "static" / "uploads" / "prospectus"
    prospectus_dir.mkdir(parents=True, exist_ok=True)
    app.config["PROSPECTUS_UPLOAD_FOLDER"] = str(prospectus_dir)

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
    compress.init_app(app)

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

    def static_exists(filename: str) -> bool:
        static_root = Path(app.static_folder or "")
        return (static_root / filename).is_file()

    def with_cache_headers(response, *, max_age: int | None = None):
        cache_seconds = max_age if max_age is not None else app.config.get("STATIC_CACHE_SECONDS", 60 * 60 * 24 * 30)
        response.cache_control.public = True
        response.cache_control.max_age = cache_seconds
        response.expires = datetime.utcnow() + timedelta(seconds=cache_seconds)
        return response

    def asset_url(filename: str, *, fallback: str | None = None) -> str:
        static_root = Path(app.static_folder or "")
        candidate = static_root / filename
        if candidate.is_file():
            version = int(candidate.stat().st_mtime)
            return url_for("static", filename=filename, v=version)

        if fallback:
            fallback_path = static_root / fallback
            if fallback_path.is_file():
                version = int(fallback_path.stat().st_mtime)
                return url_for("static", filename=fallback, v=version)
            return url_for("static", filename=fallback)

        return url_for("static", filename=filename)

    app.jinja_env.globals.update(
        asset_url=asset_url,
        static_exists=static_exists,
    )

    instance_path = Path(app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)
    app.config["DATABASE"] = str(instance_path / "lmsc.sqlite3")

    def slugify(value: str) -> str:
        value = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().lower())
        value = re.sub(r"-+", "-", value).strip("-")
        return value or "page"

    @app.before_request
    def enforce_https_redirect() -> Any:
        """Force HTTPS in production environments by issuing a 301 redirect."""

        if not app.config.get("ENABLE_HTTPS_REDIRECT", False):
            return None

        # Skip redirect for local development hosts
        host = request.host.split(":", 1)[0]
        if host in {"127.0.0.1", "localhost"}:
            return None

        proto = request.headers.get("X-Forwarded-Proto") or ("https" if request.is_secure else "http")
        if proto != "https":
            target_url = request.url.replace("http://", "https://", 1)
            return redirect(target_url, code=301)

        return None

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

    def generate_unique_blog_slug(base_slug: str, *, exclude_id: int | None = None) -> str:
        cleaned = base_slug or "blog"
        slug = cleaned
        suffix = 1
        db = get_db()

        while True:
            row = db.execute(
                "SELECT id FROM blog_posts WHERE slug = ?",
                (slug,),
            ).fetchone()
            if row is None:
                return slug
            if exclude_id is not None and int(row["id"]) == exclude_id:
                return slug
            slug = f"{cleaned}-{suffix}" if cleaned else f"blog-{suffix}"
            suffix += 1

    def generate_unique_course_slug(base_slug: str, *, exclude_id: int | None = None) -> str:
        cleaned = base_slug or "course"
        slug = cleaned
        suffix = 1
        db = get_db()

        while True:
            row = db.execute(
                "SELECT id FROM courses WHERE slug = ?",
                (slug,),
            ).fetchone()
            if row is None:
                return slug
            if exclude_id is not None and int(row["id"]) == exclude_id:
                return slug
            slug = f"{cleaned}-{suffix}" if cleaned else f"course-{suffix}"
            suffix += 1

    def allowed_image_file(filename: str) -> bool:
        if not filename or "." not in filename:
            return False
        ext = filename.rsplit(".", 1)[1].lower()
        return ext in app.config["ALLOWED_IMAGE_EXTENSIONS"]

    def build_canonical_url(slug: str) -> str:
        endpoint = PAGE_ENDPOINT_OVERRIDES.get(slug)
        if endpoint:
            return url_for(endpoint, _external=True)
        return url_for("render_dynamic_page", slug=slug, _external=True)

    def should_noindex(slug: str) -> bool:
        return slug in NOINDEX_SLUGS

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

    def save_prospectus_pdf(file_storage):
        if not file_storage or not file_storage.filename:
            raise ValueError("Please choose a PDF prospectus to upload.")
        if not allowed_policy_document(file_storage.filename):
            raise ValueError("Prospectus files must be supplied as PDF documents.")

        filename = secure_filename(file_storage.filename)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        final_name = f"{timestamp}_{filename}"
        destination = Path(app.config["PROSPECTUS_UPLOAD_FOLDER"]) / final_name
        file_storage.save(destination)
        return f"uploads/prospectus/{final_name}"

    def save_blog_image(file_storage, *, description: str) -> str:
        if not file_storage or not file_storage.filename:
            raise ValueError(f"Please choose an image for the {description} field.")
        if not allowed_image_file(file_storage.filename):
            raise ValueError(
                f"{description} images must be supplied as JPG, JPEG, PNG, WEBP, or GIF files."
            )

        filename = secure_filename(file_storage.filename)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        final_name = f"{timestamp}_{filename}"
        destination = Path(app.config["BLOG_IMAGE_UPLOAD_FOLDER"]) / final_name
        file_storage.save(destination)
        return f"uploads/blogs/{final_name}"

    def save_course_image(file_storage):
        if not file_storage or not file_storage.filename:
            raise ValueError("Please choose an image to represent the course card.")
        if not allowed_image_file(file_storage.filename):
            raise ValueError("Course images must be JPG, JPEG, PNG, WEBP, or GIF files.")

        filename = secure_filename(file_storage.filename)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        final_name = f"{timestamp}_{filename}"
        destination = Path(app.config["COURSE_IMAGE_UPLOAD_FOLDER"]) / final_name
        file_storage.save(destination)
        return f"uploads/courses/{final_name}"

    def save_carousel_image(file_storage):
        if not file_storage or not file_storage.filename:
            raise ValueError("Please choose an image for the carousel slide.")
        if not allowed_image_file(file_storage.filename):
            raise ValueError("Carousel slide images must be JPG, JPEG, PNG, WEBP, or GIF files.")

        filename = secure_filename(file_storage.filename)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        final_name = f"{timestamp}_{filename}"
        destination = Path(app.config["CAROUSEL_IMAGE_UPLOAD_FOLDER"]) / final_name
        file_storage.save(destination)
        return f"uploads/carousel/{final_name}"

    def remove_static_file(relative_path: str | None) -> None:
        if not relative_path:
            return
        target_path = Path(app.root_path) / "static" / relative_path
        try:
            target_path.unlink(missing_ok=True)
        except OSError:
            pass

    def safe_int(value: object) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def normalise_multiline(raw_value: str | None) -> str | None:
        if raw_value is None:
            return None
        lines = [line.strip() for line in raw_value.splitlines() if line.strip()]
        return "\n".join(lines) if lines else None

    def split_multiline(value: str | None) -> list[str]:
        if not value:
            return []
        return [line.strip() for line in value.splitlines() if line.strip()]

    def split_paragraphs(value: str | None) -> list[str]:
        if not value:
            return []
        chunks = re.split(r"\n{2,}", value)
        paragraphs = [chunk.strip() for chunk in chunks if chunk.strip()]
        if not paragraphs:
            # Fall back to single newlines if double-newline paragraphs absent
            return split_multiline(value)
        return paragraphs

    def apply_hero_highlights(text: str | None, highlights: str | None = None) -> Markup:
        if not text:
            return Markup("")

        highlighted: Markup = Markup(escape(text))
        if not highlights:
            return highlighted

        seen_phrases: set[str] = set()
        for phrase in split_multiline(highlights):
            trimmed = phrase.strip()
            if not trimmed or trimmed in seen_phrases:
                continue
            seen_phrases.add(trimmed)
            escaped_phrase = str(escape(trimmed))
            if escaped_phrase not in highlighted:
                continue
            replacement = Markup(
                "<span class=\"hero-underline\" data-hero-underline>"
                f"<span class=\"hero-underline__text\">{escaped_phrase}</span>"
                "<svg class=\"hero-underline__svg\" viewBox=\"0 0 200 44\" preserveAspectRatio=\"none\" aria-hidden=\"true\">"
                "<path class=\"hero-underline__path\" d=\"M4 28 Q 70 44 132 30 Q 178 20 196 26\" fill=\"none\" stroke-linecap=\"round\" stroke-width=\"6\"></path>"
                "</svg>"
                "</span>"
            )
            highlighted = Markup(highlighted.replace(escaped_phrase, replacement, 1))

        return highlighted

    def build_rich_html(value: str | None, *, as_list: bool = False) -> Markup | None:
        if not value:
            return None
        trimmed = value.strip()
        if not trimmed:
            return None
        if "<" in trimmed and ">" in trimmed:
            return Markup(trimmed)
        if as_list:
            items = split_multiline(trimmed)
            if not items:
                return None
            list_items = "".join(f"<li>{escape(item)}</li>" for item in items)
            return Markup(f"<ul>{list_items}</ul>")
        paragraphs = split_paragraphs(trimmed)
        if not paragraphs:
            return None
        html = "".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)
        return Markup(html)

    def render_rich_text(value: str | None) -> Markup:
        rich_value = build_rich_html(value)
        if rich_value is None:
            return Markup("")
        return rich_value

    app.jinja_env.filters["hero_highlight"] = apply_hero_highlights
    app.jinja_env.filters["richtext"] = render_rich_text

    def is_probably_bot(user_agent: str) -> bool:
        if not user_agent:
            return False
        lowered = user_agent.lower()
        bot_tokens = (
            "bot",
            "spider",
            "crawl",
            "slurp",
            "phantom",
            "headless",
            "pingdom",
        )
        return any(token in lowered for token in bot_tokens)

    def detect_device_details(user_agent: str) -> tuple[str, str]:
        ua = (user_agent or "").lower()
        device_type = "Desktop"
        if "ipad" in ua or "tablet" in ua:
            device_type = "Tablet"
        elif "mobile" in ua or "iphone" in ua or "android" in ua:
            device_type = "Mobile"

        device_os = "Other"
        if "windows" in ua:
            device_os = "Windows"
        elif "mac os" in ua or "macintosh" in ua:
            device_os = "macOS"
        elif "iphone" in ua or "ipad" in ua or "ios" in ua:
            device_os = "iOS"
        elif "android" in ua:
            device_os = "Android"
        elif "linux" in ua:
            device_os = "Linux"

        return device_type, device_os

    def extract_country_from_headers(req, language: str | None) -> str:
        header_keys = (
            "CF-IPCountry",
            "X-Appengine-Country",
            "X-Country-Code",
        )
        for key in header_keys:
            value = req.headers.get(key)
            if value and value not in {"", "XX"}:
                return value.upper()

        if language and "-" in language:
            return language.split("-")[-1].upper()

        return "Unknown"

    def extract_slug_from_path(path: str | None) -> str | None:
        if not path:
            return None
        clean_path = path.split("?")[0].split("#")[0]
        if clean_path == "/":
            return "home"
        stripped = clean_path.strip("/")
        if not stripped:
            return "home"
        parts = stripped.split("/")
        if parts[0] == "pages" and len(parts) > 1:
            return parts[1]
        return parts[-1]

    def classify_traffic_source(
        url: str | None,
        referrer: str | None,
        host: str,
    ) -> tuple[str, str | None, str | None, str | None, str | None]:
        traffic_source = "Direct"
        utm_source = None
        utm_medium = None
        utm_campaign = None
        referrer_domain = None

        if url:
            parsed_url = urlparse(url)
            params = parse_qs(parsed_url.query)
            utm_source = params.get("utm_source", [None])[0]
            utm_medium = params.get("utm_medium", [None])[0]
            utm_campaign = params.get("utm_campaign", [None])[0]

        if referrer:
            ref_parsed = urlparse(referrer)
            referrer_domain = ref_parsed.netloc.lower()
            if referrer_domain and referrer_domain.startswith("www."):
                referrer_domain = referrer_domain[4:]
            if referrer_domain:
                referrer_domain = referrer_domain.split(":")[0]

        host = host.lower()
        if host.startswith("www."):
            host = host[4:]
        if host:
            host = host.split(":")[0]

        if utm_medium:
            medium = utm_medium.lower()
            if medium in {"email", "newsletter"}:
                traffic_source = "Email"
            elif medium in {"cpc", "ppc", "paid", "paid-search"}:
                traffic_source = "Paid Search"
            elif medium in {"social", "paid-social"}:
                traffic_source = "Paid Social"
            elif medium in {"display", "banner"}:
                traffic_source = "Display"
            else:
                traffic_source = medium.title()
        elif referrer_domain:
            if host and referrer_domain.endswith(host):
                traffic_source = "Internal"
            elif any(token in referrer_domain for token in SOCIAL_DOMAINS):
                traffic_source = "Social"
            elif any(token in referrer_domain for token in SEARCH_DOMAINS):
                traffic_source = "Organic Search"
            else:
                traffic_source = "Referral"
        else:
            traffic_source = "Direct"

        return traffic_source, utm_source, utm_medium, utm_campaign, referrer_domain

    def compute_percent_change(current: float | int, previous: float | int) -> float | None:
        if previous in (None, 0):
            return None
        try:
            change = ((float(current) - float(previous)) / float(previous)) * 100.0
        except (TypeError, ZeroDivisionError):
            return None
        return round(change, 1)

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

    def ensure_course_schema(db: sqlite3.Connection) -> None:
        existing_columns = {
            row["name"] for row in db.execute("PRAGMA table_info(courses)").fetchall()
        }
        for column, definition in COURSE_SCHEMA_ADDITIONAL_COLUMNS.items():
            if column not in existing_columns:
                db.execute(f"ALTER TABLE courses ADD COLUMN {column} {definition}")

        db.execute(
            """
            CREATE TABLE IF NOT EXISTS course_faqs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                display_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_course_faqs_course_order ON course_faqs(course_id, display_order, id)"
        )
        db.execute("CREATE INDEX IF NOT EXISTS idx_courses_order ON courses(display_order, title)")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_courses_slug ON courses(slug)")

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
            CREATE TABLE IF NOT EXISTS consultations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                student_name TEXT,
                study_level TEXT,
                interest_area TEXT,
                meeting_mode TEXT,
                timezone TEXT,
                scheduled_date TEXT NOT NULL,
                scheduled_time TEXT NOT NULL,
                scheduled_at TEXT,
                notes TEXT,
                status TEXT NOT NULL DEFAULT 'Pending',
                source TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_consultations_date ON consultations(scheduled_date)"
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_consultations_status ON consultations(status)"
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
            CREATE TABLE IF NOT EXISTS blog_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                publish_date TEXT NOT NULL,
                summary TEXT,
                thumbnail_path TEXT,
                thumbnail_alt TEXT,
                cover_image_path TEXT,
                cover_image_alt TEXT,
                heading_one TEXT,
                text_content_one TEXT,
                picture_one_path TEXT,
                picture_one_alt TEXT,
                heading_two TEXT,
                text_content_two TEXT,
                quote_block TEXT,
                heading_three TEXT,
                picture_two_path TEXT,
                picture_two_alt TEXT,
                heading_four TEXT,
                text_content_three TEXT,
                picture_three_path TEXT,
                picture_three_alt TEXT,
                text_content_four TEXT,
                related_article_1_slug TEXT,
                related_article_2_slug TEXT,
                related_article_3_slug TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_blog_posts_publish_date ON blog_posts(publish_date)"
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
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT,
                level TEXT NOT NULL,
                title TEXT NOT NULL,
                image_path TEXT,
                image_alt TEXT,
                short_description TEXT NOT NULL,
                hours INTEGER NOT NULL,
                display_order INTEGER NOT NULL DEFAULT 0,
                about_course TEXT,
                study_topics TEXT,
                skills_built TEXT,
                audience_notes TEXT,
                exam_details TEXT,
                entry_requirements TEXT,
                course_outcome TEXT,
                progression TEXT,
                sidebar_fees TEXT,
                sidebar_summary TEXT,
                includes_items TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        ensure_course_schema(db)
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS carousel_slides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                headline TEXT NOT NULL,
                headline_highlights TEXT,
                body TEXT,
                cta_label TEXT,
                cta_url TEXT,
                image_path TEXT,
                image_alt TEXT,
                display_order INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_carousel_order ON carousel_slides(is_active, display_order, id)"
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS prospectus_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_label TEXT NOT NULL,
                description TEXT,
                document_path TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_prospectus_active ON prospectus_versions(is_active)"
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visitor_id TEXT,
                session_id TEXT,
                page_slug TEXT,
                page_title TEXT,
                path TEXT,
                url TEXT,
                referrer TEXT,
                referrer_domain TEXT,
                traffic_source TEXT,
                utm_source TEXT,
                utm_medium TEXT,
                utm_campaign TEXT,
                device_type TEXT,
                device_os TEXT,
                language TEXT,
                country TEXT,
                timezone TEXT,
                screen_width INTEGER,
                screen_height INTEGER,
                is_session_start INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_analytics_created_at ON analytics_events(created_at)"
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_analytics_session ON analytics_events(session_id)"
        )
        db.execute(
            "CREATE INDEX IF NOT EXISTS idx_analytics_slug ON analytics_events(page_slug)"
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

            if nav_display and nav_display != existing["nav_display"]:
                updates.append("nav_display = ?")
                params.append(nav_display)

            if nav_order and nav_order != existing["nav_order"]:
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

    def fetch_blog_posts(*, limit: int | None = None, exclude_id: int | None = None) -> list[sqlite3.Row]:
        db = get_db()
        query = "SELECT * FROM blog_posts"
        params: list[Any] = []
        if exclude_id is not None:
            query += " WHERE id != ?"
            params.append(exclude_id)
        query += " ORDER BY datetime(publish_date) DESC, datetime(created_at) DESC"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        return db.execute(query, params).fetchall()

    def get_blog_post(post_id: int) -> sqlite3.Row | None:
        db = get_db()
        return db.execute(
            "SELECT * FROM blog_posts WHERE id = ?",
            (post_id,),
        ).fetchone()

    def get_blog_post_by_slug(slug: str) -> sqlite3.Row | None:
        db = get_db()
        return db.execute(
            "SELECT * FROM blog_posts WHERE slug = ?",
            (slug,),
        ).fetchone()

    def create_blog_post(data: dict[str, Any]) -> int:
        db = get_db()
        now = current_timestamp()
        columns = ", ".join(BLOG_DB_COLUMNS)
        placeholders = ", ".join(["?"] * len(BLOG_DB_COLUMNS))
        values = [data.get(column) for column in BLOG_DB_COLUMNS]
        cursor = db.execute(
            f"INSERT INTO blog_posts ({columns}, created_at, updated_at) VALUES ({placeholders}, ?, ?)",
            values + [now, now],
        )
        db.commit()
        return int(cursor.lastrowid)

    def update_blog_post(post_id: int, data: dict[str, Any]) -> None:
        db = get_db()
        now = current_timestamp()
        set_clause = ", ".join(f"{column} = ?" for column in BLOG_DB_COLUMNS)
        values = [data.get(column) for column in BLOG_DB_COLUMNS]
        values.extend([now, post_id])
        db.execute(
            f"UPDATE blog_posts SET {set_clause}, updated_at = ? WHERE id = ?",
            values,
        )
        db.commit()

    def delete_blog_post(post_id: int) -> None:
        db = get_db()
        db.execute("DELETE FROM blog_posts WHERE id = ?", (post_id,))
        db.commit()

    def fetch_courses(*, limit: int | None = None) -> list[sqlite3.Row]:
        db = get_db()
        query = "SELECT * FROM courses ORDER BY display_order ASC, title ASC, id ASC"
        params: list[Any] = []
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        return db.execute(query, params).fetchall()

    def build_related_course_options(*, exclude_id: int | None = None) -> list[dict[str, Any]]:
        options: list[dict[str, Any]] = []
        for row in fetch_courses():
            row_id = int(row["id"])
            if exclude_id is not None and row_id == exclude_id:
                continue
            slug_value = (row.get("slug") if isinstance(row, dict) else row["slug"]) or ""
            title_value = (row.get("title") if isinstance(row, dict) else row["title"]) or ""
            if not slug_value or not title_value:
                continue
            options.append({
                "id": row_id,
                "slug": slug_value,
                "title": title_value,
            })
        options.sort(key=lambda option: option["title"].casefold())
        return options

    def fetch_course_stats() -> dict[str, Any]:
        db = get_db()
        row = db.execute(
            "SELECT COUNT(*) AS total, MAX(updated_at) AS last_updated FROM courses"
        ).fetchone()
        total = int(row["total"]) if row and row["total"] is not None else 0
        with_images = 0
        if total:
            with_images = int(
                db.execute(
                    "SELECT COUNT(*) FROM courses WHERE image_path IS NOT NULL AND image_path != ''"
                ).fetchone()[0]
            )
        return {
            "total": total,
            "with_images": with_images,
            "last_updated": row["last_updated"],
        }

    def get_course_by_id(course_id: int) -> sqlite3.Row | None:
        db = get_db()
        return db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()

    def get_course_by_slug(slug: str) -> sqlite3.Row | None:
        db = get_db()
        return db.execute("SELECT * FROM courses WHERE slug = ?", (slug,)).fetchone()

    def fetch_course_faqs(course_id: int) -> list[sqlite3.Row]:
        db = get_db()
        return db.execute(
            "SELECT * FROM course_faqs WHERE course_id = ? ORDER BY display_order ASC, id ASC",
            (course_id,),
        ).fetchall()

    def replace_course_faqs(course_id: int, items: list[dict[str, Any]]) -> None:
        db = get_db()
        db.execute("DELETE FROM course_faqs WHERE course_id = ?", (course_id,))
        if not items:
            db.commit()
            return
        now = current_timestamp()
        for position, item in enumerate(items):
            db.execute(
                """
                INSERT INTO course_faqs (
                    course_id,
                    question,
                    answer,
                    display_order,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    course_id,
                    item["question"],
                    item["answer"],
                    position,
                    now,
                    now,
                ),
            )
        db.commit()

    def create_course(data: dict[str, Any]) -> int:
        db = get_db()
        now = current_timestamp()
        columns = ", ".join(COURSE_DB_COLUMNS)
        placeholders = ", ".join(["?"] * len(COURSE_DB_COLUMNS))
        values = [data.get(column) for column in COURSE_DB_COLUMNS]
        cursor = db.execute(
            f"INSERT INTO courses ({columns}, created_at, updated_at) VALUES ({placeholders}, ?, ?)",
            values + [now, now],
        )
        db.commit()
        return int(cursor.lastrowid)

    def update_course(course_id: int, data: dict[str, Any]) -> None:
        db = get_db()
        now = current_timestamp()
        set_clause = ", ".join(f"{column} = ?" for column in COURSE_DB_COLUMNS)
        values = [data.get(column) for column in COURSE_DB_COLUMNS]
        values.extend([now, course_id])
        db.execute(
            f"UPDATE courses SET {set_clause}, updated_at = ? WHERE id = ?",
            values,
        )
        db.commit()

    def delete_course(course_id: int) -> None:
        existing = get_course_by_id(course_id)
        if existing is None:
            return
        if isinstance(existing, sqlite3.Row):
            image_path = existing["image_path"]
        elif isinstance(existing, dict):
            image_path = existing.get("image_path")
        else:
            image_path = None
        if image_path and isinstance(image_path, str) and image_path.startswith("uploads/"):
            remove_static_file(image_path)
        db = get_db()
        db.execute("DELETE FROM course_faqs WHERE course_id = ?", (course_id,))
        db.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        db.commit()

    def fetch_carousel_slides(*, include_inactive: bool = False) -> list[sqlite3.Row]:
        db = get_db()
        query = "SELECT * FROM carousel_slides"
        params: list[Any] = []
        if not include_inactive:
            query += " WHERE is_active = 1"
        query += " ORDER BY COALESCE(display_order, 0) ASC, id ASC"
        return db.execute(query, params).fetchall()

    def get_carousel_slide(slide_id: int) -> sqlite3.Row | None:
        db = get_db()
        return db.execute("SELECT * FROM carousel_slides WHERE id = ?", (slide_id,)).fetchone()

    def create_carousel_slide(data: dict[str, Any]) -> int:
        db = get_db()
        now = current_timestamp()
        cursor = db.execute(
            """
            INSERT INTO carousel_slides (
                headline,
                headline_highlights,
                body,
                cta_label,
                cta_url,
                image_path,
                image_alt,
                display_order,
                is_active,
                created_at,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("headline"),
                data.get("headline_highlights"),
                data.get("body"),
                data.get("cta_label"),
                data.get("cta_url"),
                data.get("image_path"),
                data.get("image_alt"),
                int(data.get("display_order") or 0),
                1 if data.get("is_active") else 0,
                now,
                now,
            ),
        )
        db.commit()
        return int(cursor.lastrowid)

    def update_carousel_slide(slide_id: int, data: dict[str, Any]) -> None:
        db = get_db()
        now = current_timestamp()
        db.execute(
            """
            UPDATE carousel_slides
            SET headline = ?,
                headline_highlights = ?,
                body = ?,
                cta_label = ?,
                cta_url = ?,
                image_path = ?,
                image_alt = ?,
                display_order = ?,
                is_active = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                data.get("headline"),
                data.get("headline_highlights"),
                data.get("body"),
                data.get("cta_label"),
                data.get("cta_url"),
                data.get("image_path"),
                data.get("image_alt"),
                int(data.get("display_order") or 0),
                1 if data.get("is_active") else 0,
                now,
                slide_id,
            ),
        )
        db.commit()

    def delete_carousel_slide(slide_id: int) -> None:
        slide = get_carousel_slide(slide_id)
        if slide is None:
            return
        image_path = slide["image_path"]
        if image_path and isinstance(image_path, str) and image_path.startswith("uploads/"):
            remove_static_file(image_path)
        db = get_db()
        db.execute("DELETE FROM carousel_slides WHERE id = ?", (slide_id,))
        db.commit()

    def fetch_carousel_stats() -> dict[str, Any]:
        db = get_db()
        row = db.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active_count,
                MAX(updated_at) AS last_updated
            FROM carousel_slides
            """
        ).fetchone()
        total = int(row["total"]) if row and row["total"] is not None else 0
        active = int(row["active_count"]) if row and row["active_count"] is not None else 0
        return {
            "total": total,
            "active": active,
            "last_updated": row["last_updated"] if row else None,
        }

    def ensure_default_courses() -> None:
        if not app.config.get("SEED_DEFAULT_COURSES", True):
            ensure_course_slugs()
            return

        seed_marker = Path(app.instance_path) / "courses_seeded.flag"
        db = get_db()
        row = db.execute("SELECT COUNT(*) AS total FROM courses").fetchone()
        existing_total = int(row["total"] or 0) if row and row["total"] is not None else 0

        if existing_total > 0:
            ensure_course_slugs()
            if not seed_marker.exists():
                try:
                    seed_marker.write_text(current_timestamp())
                except OSError:
                    pass
            return

        if seed_marker.exists():
            return

        for seed in DEFAULT_COURSE_SEED:
            payload = {column: seed.get(column) for column in COURSE_DB_COLUMNS}
            title_value = seed.get("title", "Course")
            seed_slug_source = seed.get("slug") or title_value
            slug_base = slugify(seed_slug_source)
            payload["slug"] = generate_unique_course_slug(slug_base)
            payload["level"] = seed.get("level")
            payload["title"] = title_value
            payload["image_path"] = seed.get("image_path")
            payload["image_alt"] = seed.get("image_alt")
            payload["short_description"] = seed.get("short_description")
            payload["hours"] = int(seed.get("hours", 0) or 0)
            payload["display_order"] = int(seed.get("display_order", 0) or 0)

            # Provide sane defaults for optional text blocks
            for column in COURSE_DB_COLUMNS:
                if payload.get(column) is None:
                    payload[column] = None

            create_course(payload)

        ensure_course_slugs()
        try:
            seed_marker.write_text(current_timestamp())
        except OSError:
            pass

    def ensure_course_slugs() -> None:
        db = get_db()
        rows = db.execute(
            "SELECT id, title FROM courses WHERE slug IS NULL OR slug = ''"
        ).fetchall()
        if not rows:
            return
        now = current_timestamp()
        for row in rows:
            title_value = row["title"] or f"course-{row['id']}"
            candidate = slugify(title_value)
            slug_value = generate_unique_course_slug(candidate, exclude_id=int(row["id"]))
            db.execute(
                "UPDATE courses SET slug = ?, updated_at = ? WHERE id = ?",
                (slug_value, now, row["id"]),
            )
        db.commit()

    def ensure_default_carousel_slides() -> None:
        db = get_db()
        row = db.execute("SELECT COUNT(*) AS total FROM carousel_slides").fetchone()
        existing_total = int(row["total"]) if row and row["total"] is not None else 0
        if existing_total > 0:
            return

        for index, seed in enumerate(DEFAULT_CAROUSEL_SLIDES, start=1):
            create_carousel_slide(
                {
                    "headline": seed.get("headline", ""),
                    "headline_highlights": normalise_multiline(seed.get("headline_highlights")),
                    "body": seed.get("body"),
                    "cta_label": seed.get("cta_label"),
                    "cta_url": seed.get("cta_url"),
                    "image_path": seed.get("image_path"),
                    "image_alt": seed.get("image_alt"),
                    "display_order": int(seed.get("display_order", index) or index),
                    "is_active": 1 if seed.get("is_active", 1) else 0,
                }
            )

    def fetch_related_blog_posts(
        related_slugs: Sequence[str | None], *, exclude_id: int | None = None, limit: int = 3
    ) -> list[sqlite3.Row]:
        desired = max(limit, 0)
        if desired == 0:
            return []

        seen_ids: set[int] = set()
        results: list[sqlite3.Row] = []
        for slug in related_slugs:
            if not slug:
                continue
            candidate = get_blog_post_by_slug(slug)
            if candidate is None:
                continue
            candidate_id = int(candidate["id"])
            if exclude_id is not None and candidate_id == exclude_id:
                continue
            if candidate_id in seen_ids:
                continue
            results.append(candidate)
            seen_ids.add(candidate_id)
            if len(results) >= desired:
                return results[:desired]

        if len(results) < desired:
            fallback_posts = fetch_blog_posts(limit=desired * 2, exclude_id=exclude_id)
            for row in fallback_posts:
                row_id = int(row["id"])
                if row_id in seen_ids:
                    continue
                results.append(row)
                seen_ids.add(row_id)
                if len(results) >= desired:
                    break

        return results[:desired]

    def collect_blog_payload(existing: sqlite3.Row | None = None) -> tuple[dict[str, Any], list[str], list[str]]:
        data: dict[str, Any] = {}
        errors: list[str] = []
        notices: list[str] = []
        existing_dict = dict(existing) if existing is not None else {}

        title = request.form.get("title", "").strip()
        if not title:
            errors.append("Please provide a blog title.")
        data["title"] = title

        slug_input = request.form.get("slug", "").strip()
        base_slug = slugify(slug_input or title)
        if not base_slug:
            base_slug = "blog"
        exclude_id = int(existing_dict.get("id")) if existing_dict.get("id") else None
        unique_slug = generate_unique_blog_slug(base_slug, exclude_id=exclude_id)
        data["slug"] = unique_slug
        if slug_input and slugify(slug_input) != unique_slug:
            notices.append("The slug was adjusted to remain unique.")
        elif not slug_input and unique_slug != base_slug:
            notices.append("A unique slug was generated for this title.")

        publish_date_raw = request.form.get("publish_date", "").strip()
        if not publish_date_raw:
            errors.append("Please choose a publish date.")
        else:
            try:
                datetime.strptime(publish_date_raw, "%Y-%m-%d")
            except ValueError:
                errors.append("Publish date must follow the YYYY-MM-DD format.")
        data["publish_date"] = publish_date_raw

        summary = request.form.get("summary", "").strip()
        if not summary:
            errors.append("Please add a short summary for the article.")
        data["summary"] = summary

        def clean_optional(field_name: str) -> str | None:
            value = request.form.get(field_name)
            if value is None:
                return None
            cleaned = value.strip()
            return cleaned or None

        data["heading_one"] = clean_optional("heading_one")
        data["text_content_one"] = clean_optional("text_content_one")
        data["heading_two"] = clean_optional("heading_two")
        data["text_content_two"] = clean_optional("text_content_two")
        data["quote_block"] = clean_optional("quote_block")
        data["heading_three"] = clean_optional("heading_three")
        data["heading_four"] = clean_optional("heading_four")
        data["text_content_three"] = clean_optional("text_content_three")
        data["text_content_four"] = clean_optional("text_content_four")

        for field_name, (path_column, alt_column, _) in BLOG_IMAGE_FIELD_MAP.items():
            data[path_column] = existing_dict.get(path_column)
            alt_value = request.form.get(f"{field_name}_alt", "")
            data[alt_column] = alt_value.strip() or None

        for index, relation_column in enumerate(BLOG_RELATION_FIELDS, start=1):
            raw_relation = request.form.get(relation_column, "").strip()
            relation_slug = slugify(raw_relation) if raw_relation else None
            if relation_slug and relation_slug == unique_slug:
                errors.append(f"Related article {index} cannot reference the same article.")
            data[relation_column] = relation_slug

        return data, errors, notices

    def collect_course_payload(
        existing: sqlite3.Row | None = None,
    ) -> tuple[dict[str, Any], list[str], list[str], list[dict[str, str]], dict[str, list[Any]]]:
        data: dict[str, Any] = {}
        errors: list[str] = []
        notices: list[str] = []
        list_values: dict[str, list[Any]] = {}
        faq_items: list[dict[str, str]] = []
        existing_dict = dict(existing) if existing is not None else {}

        def clean_text(field_name: str) -> str:
            return request.form.get(field_name, "").strip()

        level = clean_text("level")
        if not level:
            errors.append("Please supply a course level label (e.g. A Level, GCSE, Online).")
        data["level"] = level

        title = clean_text("title")
        if not title:
            errors.append("Please add a course title.")
        data["title"] = title

        description = clean_text("short_description")
        if not description:
            errors.append("Please provide a short course description.")
        data["short_description"] = description

        hours_value = safe_int(request.form.get("hours"))
        if hours_value is None or hours_value <= 0:
            errors.append("Number of hours must be a positive number.")
        data["hours"] = hours_value or 0

        display_order_value = safe_int(request.form.get("display_order"))
        if display_order_value is None:
            display_order_value = existing_dict.get("display_order", 0) or 0
        data["display_order"] = display_order_value

        slug_input = clean_text("slug")
        title_basis = title or existing_dict.get("title", "")
        base_slug = slugify(slug_input or title_basis or "course")
        exclude_id = int(existing_dict.get("id")) if existing_dict.get("id") else None
        unique_slug = generate_unique_course_slug(base_slug, exclude_id=exclude_id)
        data["slug"] = unique_slug
        if slug_input and slugify(slug_input) != unique_slug:
            notices.append("The course slug was adjusted to remain unique.")
        elif not slug_input and unique_slug != base_slug:
            notices.append("A unique slug was generated for this course.")

        seen_relations: set[str] = set()
        for index, field in enumerate(COURSE_RELATION_FIELDS, start=1):
            raw_value = request.form.get(field, "") or ""
            cleaned_value = raw_value.strip()
            if not cleaned_value:
                data[field] = None
                continue

            relation_slug = slugify(cleaned_value)
            data[field] = relation_slug

            if not relation_slug:
                errors.append(f"Related course {index} is invalid.")
                continue

            if relation_slug == unique_slug:
                errors.append(f"Related course {index} cannot reference the same course.")
                continue

            if relation_slug in seen_relations:
                errors.append("Please choose different related courses.")
                continue

            related_course = get_course_by_slug(relation_slug)
            if related_course is None:
                errors.append(f"Related course {index} could not be found.")
                continue

            if existing_dict.get("id") and int(related_course["id"]) == int(existing_dict["id"]):
                errors.append(f"Related course {index} cannot reference the same course.")
                continue

            seen_relations.add(relation_slug)

        for field in COURSE_TEXT_BLOCK_FIELDS:
            value = request.form.get(field, "")
            cleaned = value.strip()
            if not cleaned:
                readable = field.replace("_", " ")
                errors.append(f"Please provide content for {readable}.")
            data[field] = cleaned or None

        sidebar_fees = clean_text("sidebar_fees")
        if not sidebar_fees:
            errors.append("Please add fee information for the course sidebar.")
        data["sidebar_fees"] = sidebar_fees or None

        includes_items = [item.strip() for item in request.form.getlist("includes_items[]") if item.strip()]
        if not includes_items:
            includes_text = request.form.get("includes_items", "")
            includes_items = [line.strip() for line in includes_text.splitlines() if line.strip()]
        if not includes_items:
            errors.append('Please add at least one bullet for the "This course includes" section.')
        list_values["includes_items"] = includes_items
        data["includes_items"] = "\n".join(includes_items) if includes_items else None

        custom_content_raw = request.form.get("custom_content", "")
        custom_content_clean = custom_content_raw.strip()
        data["custom_content"] = custom_content_clean or None

        image_alt = clean_text("image_alt")
        data["image_alt"] = image_alt or None
        current_image = existing_dict.get("image_path")
        data["image_path"] = current_image

        faq_questions = request.form.getlist("faq_questions[]")
        faq_answers = request.form.getlist("faq_answers[]")
        max_length = max(len(faq_questions), len(faq_answers))
        for index in range(max_length):
            question_raw = faq_questions[index] if index < len(faq_questions) else ""
            answer_raw = faq_answers[index] if index < len(faq_answers) else ""
            question = question_raw.strip()
            answer = answer_raw.strip()
            if not question and not answer:
                continue
            if not question:
                errors.append(f"FAQ entry {index + 1} is missing a question.")
                continue
            if not answer:
                errors.append(f"FAQ entry {index + 1} is missing an answer.")
                continue
            faq_items.append({"question": question, "answer": answer})
        list_values["faq_items"] = faq_items

        return data, errors, notices, faq_items, list_values

    def collect_carousel_payload(
        existing: sqlite3.Row | None = None,
    ) -> tuple[dict[str, Any], list[str]]:
        data: dict[str, Any] = {}
        errors: list[str] = []
        existing_dict = dict(existing) if existing is not None else {}

        def clean(field_name: str) -> str:
            return request.form.get(field_name, "").strip()

        headline = clean("headline")
        if not headline:
            errors.append("Please provide a headline for the slide.")
        data["headline"] = headline

        highlights_input = request.form.get("headline_highlights")
        data["headline_highlights"] = (
            normalise_multiline(highlights_input) if highlights_input is not None else None
        )

        body_value = request.form.get("body", "")
        data["body"] = body_value.strip() or None

        cta_label = clean("cta_label") or None
        cta_url = clean("cta_url") or None
        if bool(cta_label) != bool(cta_url):
            errors.append("Please provide both a CTA label and URL, or leave both blank.")
        data["cta_label"] = cta_label
        if cta_url and not re.match(r"^https?://", cta_url) and not cta_url.startswith("/"):
            cta_url = f"/{cta_url}"
        data["cta_url"] = cta_url

        image_alt = clean("image_alt") or None
        data["image_alt"] = image_alt

        display_raw = request.form.get("display_order", "").strip()
        display_value = safe_int(display_raw)
        if display_value is None:
            if display_raw:
                errors.append("Display order must be a whole number.")
            display_value = existing_dict.get("display_order") or 0
        elif display_value < 0:
            errors.append("Display order cannot be negative.")
        data["display_order"] = display_value

        data["is_active"] = 1 if request.form.get("is_active") == "on" else 0

        return data, errors

    def process_blog_images(
        data: dict[str, Any], *, existing: sqlite3.Row | None = None, require_primary: bool = False
    ) -> list[str]:
        errors: list[str] = []
        existing_dict = dict(existing) if existing is not None else {}
        plans: dict[str, dict[str, Any]] = {}

        for field_name, (path_column, alt_column, label) in BLOG_IMAGE_FIELD_MAP.items():
            upload = request.files.get(field_name)
            has_upload = bool(upload and upload.filename)
            remove_flag = request.form.get(f"remove_{field_name}") == "on"
            current_path = existing_dict.get(path_column)
            current_alt = existing_dict.get(alt_column)
            alt_value = data.get(alt_column)
            if isinstance(alt_value, str):
                alt_value = alt_value.strip()
            action = "keep"

            if has_upload:
                if not alt_value:
                    errors.append(f"Please provide alt text for the {label} image.")
                else:
                    action = "upload"
            elif remove_flag:
                action = "remove"
                alt_value = None
            else:
                if current_path and not alt_value:
                    if current_alt:
                        alt_value = current_alt
                    else:
                        errors.append(f"Please supply alt text for the existing {label} image.")

            plans[field_name] = {
                "action": action,
                "upload": upload if has_upload else None,
                "current_path": current_path,
                "alt": alt_value,
                "label": label,
                "path_column": path_column,
                "alt_column": alt_column,
            }

            data[alt_column] = alt_value

        if require_primary:
            for required_field in ("thumbnail", "cover_image"):
                plan = plans.get(required_field, {})
                will_have = False
                if plan:
                    if plan["action"] == "upload":
                        will_have = True
                    elif plan["action"] == "keep" and plan.get("current_path"):
                        will_have = True
                if not will_have:
                    label = plans.get(required_field, {}).get("label", required_field.replace("_", " "))
                    errors.append(f"Please upload a {label} image for the article.")

        if errors:
            return errors

        for field_name, plan in plans.items():
            path_column = plan["path_column"]
            alt_column = plan["alt_column"]
            label = plan["label"]
            action = plan["action"]
            current_path = plan["current_path"]

            if action == "upload":
                upload = plan["upload"]
                if upload is None:
                    errors.append(f"Unable to process the {label} image upload.")
                    data[path_column] = current_path
                    data[alt_column] = plan["alt"]
                    continue
                try:
                    new_path = save_blog_image(upload, description=label)
                except ValueError as exc:
                    errors.append(str(exc))
                    data[path_column] = current_path
                    data[alt_column] = plan["alt"]
                    continue
                if current_path and current_path != new_path:
                    remove_static_file(current_path)
                data[path_column] = new_path
                data[alt_column] = plan["alt"]
            elif action == "remove":
                if current_path:
                    remove_static_file(current_path)
                data[path_column] = None
                data[alt_column] = None
            else:
                data[path_column] = current_path
                data[alt_column] = plan["alt"]

        return errors

    @app.template_filter("format_date")
    def format_date_filter(value: str | None, fmt: str = "%b %d, %Y") -> str:
        if not value:
            return ""
        for pattern in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = datetime.strptime(value, pattern)
                return parsed.strftime(fmt)
            except ValueError:
                continue
        return value

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

    def fetch_prospectus_versions() -> list[sqlite3.Row]:
        db = get_db()
        return db.execute(
            "SELECT * FROM prospectus_versions ORDER BY datetime(created_at) DESC, id DESC"
        ).fetchall()

    def get_prospectus_version(version_id: int) -> sqlite3.Row | None:
        db = get_db()
        return db.execute(
            "SELECT * FROM prospectus_versions WHERE id = ?",
            (version_id,),
        ).fetchone()

    def get_active_prospectus_version() -> sqlite3.Row | None:
        db = get_db()
        return db.execute(
            """
            SELECT * FROM prospectus_versions
            WHERE is_active = 1
            ORDER BY datetime(updated_at) DESC, datetime(created_at) DESC, id DESC
            LIMIT 1
            """
        ).fetchone()

    def create_prospectus_version(
        *,
        version_label: str,
        description: str | None,
        document_path: str,
        activate_now: bool = False,
    ) -> int:
        db = get_db()
        now = current_timestamp()
        if activate_now:
            db.execute(
                "UPDATE prospectus_versions SET is_active = 0, updated_at = ? WHERE is_active = 1",
                (now,),
            )
        cursor = db.execute(
            """
            INSERT INTO prospectus_versions (
                version_label,
                description,
                document_path,
                is_active,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                version_label,
                description,
                document_path,
                1 if activate_now else 0,
                now,
                now,
            ),
        )
        db.commit()
        return int(cursor.lastrowid)

    def set_active_prospectus_version(version_id: int) -> bool:
        db = get_db()
        version = get_prospectus_version(version_id)
        if version is None:
            return False

        now = current_timestamp()
        db.execute(
            "UPDATE prospectus_versions SET is_active = 0 WHERE is_active = 1 AND id != ?",
            (version_id,),
        )
        db.execute(
            "UPDATE prospectus_versions SET is_active = 1, updated_at = ? WHERE id = ?",
            (now, version_id),
        )
        db.commit()
        return True

    def delete_prospectus_version(version_id: int) -> None:
        db = get_db()
        db.execute("DELETE FROM prospectus_versions WHERE id = ?", (version_id,))
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
        page_dict: dict[str, Any] | None = None
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

        if not context.get("canonical_url"):
            try:
                context["canonical_url"] = build_canonical_url(slug)
            except Exception:
                context["canonical_url"] = request.base_url

        robots_meta = context.get("meta_robots")
        if not robots_meta and page_dict is not None:
            robots_meta = page_dict.get("meta_robots")
        if robots_meta:
            context["meta_robots"] = robots_meta
        elif robots_meta is None and should_noindex(slug):
            context["meta_robots"] = "noindex, nofollow"

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
            existing = db.execute(
                "SELECT id FROM pages WHERE slug = ?",
                (slug,),
            ).fetchone()
            if existing is not None:
                page_id = int(existing["id"])

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

    def ensure_consultation_page_seed() -> None:
        db = get_db()
        existing = db.execute(
            "SELECT id FROM pages WHERE slug = ?",
            ("book-a-consultation",),
        ).fetchone()
        if existing is not None:
            return

        seed = next(
            (item for item in DEFAULT_PAGE_SEEDS if item.get("slug") == "book-a-consultation"),
            None,
        )
        if seed is None:
            return

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
                seed["slug"],
                seed["page_name"],
                seed.get("seo_title"),
                seed.get("meta_description"),
                seed.get("nav_display", "hidden"),
                int(seed.get("nav_order", 0)),
                seed["template_name"],
                now,
                now,
            ),
        )
        db.commit()

    def create_consultation_booking(data: dict[str, Any]) -> int:
        db = get_db()
        now = current_timestamp()
        cursor = db.execute(
            """
            INSERT INTO consultations (
                full_name,
                email,
                phone,
                student_name,
                study_level,
                interest_area,
                meeting_mode,
                timezone,
                scheduled_date,
                scheduled_time,
                scheduled_at,
                notes,
                status,
                source,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("full_name"),
                data.get("email"),
                data.get("phone"),
                data.get("student_name"),
                data.get("study_level"),
                data.get("interest_area"),
                data.get("meeting_mode"),
                data.get("timezone"),
                data.get("scheduled_date"),
                data.get("scheduled_time"),
                data.get("scheduled_at"),
                data.get("notes"),
                data.get("status", "Pending"),
                data.get("source"),
                now,
                now,
            ),
        )
        db.commit()
        return int(cursor.lastrowid)

    def get_consultation(consultation_id: int) -> sqlite3.Row | None:
        db = get_db()
        return db.execute(
            "SELECT * FROM consultations WHERE id = ?",
            (consultation_id,),
        ).fetchone()

    def fetch_consultations(
        *,
        status: str | None = None,
        upcoming_only: bool = False,
        limit: int | None = None,
    ) -> list[sqlite3.Row]:
        db = get_db()
        query = "SELECT * FROM consultations"
        conditions: list[str] = []
        params: list[Any] = []

        if status:
            conditions.append("status = ?")
            params.append(status)

        if upcoming_only:
            conditions.append(
                "(scheduled_at IS NOT NULL AND datetime(scheduled_at) >= datetime('now'))"
            )

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        order_direction = "ASC" if upcoming_only else "DESC"
        query += (
            f" ORDER BY CASE WHEN scheduled_at IS NULL THEN 1 ELSE 0 END, "
            f"datetime(scheduled_at) {order_direction}, datetime(created_at) DESC"
        )

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        return db.execute(query, params).fetchall()

    def fetch_recent_consultations(limit: int = 10) -> list[sqlite3.Row]:
        return fetch_consultations(limit=limit)

    def fetch_upcoming_consultations(limit: int = 5) -> list[sqlite3.Row]:
        return fetch_consultations(upcoming_only=True, limit=limit)

    def update_consultation_status_db(consultation_id: int, status: str) -> None:
        db = get_db()
        db.execute(
            "UPDATE consultations SET status = ?, updated_at = ? WHERE id = ?",
            (status, current_timestamp(), consultation_id),
        )
        db.commit()

    def update_consultation_fields(consultation_id: int, **fields: Any) -> None:
        allowed_columns = {
            "full_name",
            "email",
            "phone",
            "student_name",
            "study_level",
            "interest_area",
            "meeting_mode",
            "timezone",
            "scheduled_date",
            "scheduled_time",
            "scheduled_at",
            "notes",
            "status",
            "source",
        }
        updates = {key: value for key, value in fields.items() if key in allowed_columns}
        if not updates:
            return

        assignments = ", ".join(f"{column} = ?" for column in updates.keys())
        params = list(updates.values())
        params.extend([current_timestamp(), consultation_id])

        db = get_db()
        db.execute(
            f"UPDATE consultations SET {assignments}, updated_at = ? WHERE id = ?",
            params,
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
        ensure_consultation_page_seed()
        ensure_default_courses()
        ensure_default_carousel_slides()

    @app.route("/robots.txt")
    def robots_txt():
        response = send_from_directory(app.static_folder, "robots.txt", mimetype="text/plain")
        return with_cache_headers(response)

    @app.route("/llms.txt")
    def llms_txt():
        response = send_from_directory(app.static_folder, "llms.txt", mimetype="text/plain")
        return with_cache_headers(response)

    @app.route("/sitemap.xml")
    def sitemap_xml():
        response = send_from_directory(app.static_folder, "sitemap.xml", mimetype="application/xml")
        return with_cache_headers(response)

    @app.route("/sitemap_index.xml")
    def sitemap_index_xml():
        response = send_from_directory(app.static_folder, "sitemap_index.xml", mimetype="application/xml")
        return with_cache_headers(response)

    @app.route("/")
    def index() -> str:
        slide_rows = fetch_carousel_slides()
        slides = [dict(row) for row in slide_rows]
        if not slides:
            slides = [dict(seed) for seed in DEFAULT_CAROUSEL_SLIDES]
        return render_site_page("index.html", "home", carousel_slides=slides)

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
        course_rows = fetch_courses()
        return render_site_page("courses.html", "courses", courses=course_rows)

    @app.route("/course-details", endpoint="course_details_legacy")
    def course_details_legacy() -> ResponseReturnValue:
        course_rows = fetch_courses(limit=1)
        if not course_rows:
            abort(404)
        first_course = course_rows[0]
        return redirect(url_for("course_details", slug=first_course["slug"]))

    @app.route("/courses/<slug>")
    def course_details(slug: str) -> ResponseReturnValue:
        course_row = get_course_by_slug(slug)
        if course_row is None:
            abort(404)

        course_dict = dict(course_row)
        course_id = int(course_dict["id"])

        study_topics_html = build_rich_html(course_dict.get("study_topics"), as_list=True)
        skills_built_html = build_rich_html(course_dict.get("skills_built"), as_list=True)
        audience_notes_html = build_rich_html(course_dict.get("audience_notes"), as_list=True)
        includes_items = split_multiline(course_dict.get("includes_items"))

        about_html = build_rich_html(course_dict.get("about_course"))
        exam_html = build_rich_html(course_dict.get("exam_details"))
        entry_html = build_rich_html(course_dict.get("entry_requirements"))
        outcome_html = build_rich_html(course_dict.get("course_outcome"))
        progression_html = build_rich_html(course_dict.get("progression"))

        faq_rows = fetch_course_faqs(course_id)
        faq_items = [dict(row) for row in faq_rows]

        relation_slugs = [course_dict.get(field) for field in COURSE_RELATION_FIELDS]
        related_courses: list[dict[str, Any]] = []
        seen_course_ids: set[int] = {course_id}

        for slug in relation_slugs:
            if not slug:
                continue
            candidate = get_course_by_slug(str(slug))
            if candidate is None:
                continue
            candidate_id = int(candidate["id"])
            if candidate_id in seen_course_ids:
                continue
            related_courses.append(dict(candidate))
            seen_course_ids.add(candidate_id)
            if len(related_courses) >= 3:
                break

        if len(related_courses) < 3:
            for row in fetch_courses():
                row_id = int(row["id"])
                if row_id in seen_course_ids:
                    continue
                related_courses.append(dict(row))
                seen_course_ids.add(row_id)
                if len(related_courses) >= 3:
                    break

        page_title = f"{course_dict['title']} | London Maths & Science College"
        meta_description = course_dict.get("short_description") or course_dict.get("sidebar_summary")

        return render_template(
            "course_details.html",
            course=course_dict,
            page_title=page_title,
            meta_description=meta_description,
            canonical_url=url_for("course_details", slug=course_dict["slug"], _external=True),
            about_html=about_html,
            study_topics_html=study_topics_html,
            skills_built_html=skills_built_html,
            audience_notes_html=audience_notes_html,
            exam_html=exam_html,
            entry_html=entry_html,
            outcome_html=outcome_html,
            progression_html=progression_html,
            includes_items=includes_items,
            faq_items=faq_items,
            related_courses=related_courses,
        )

    @app.route("/prospectus")
    def prospectus() -> str:
        active_version_row = get_active_prospectus_version()
        active_version: dict[str, Any] | None = (
            dict(active_version_row) if active_version_row is not None else None
        )
        document_url: str | None = None
        last_updated: str | None = None

        download_name: str | None = None

        if active_version is not None:
            document_url = url_for("static", filename=active_version["document_path"])
            last_updated = active_version.get("updated_at") or active_version.get("created_at")
            safe_stub = secure_filename(str(active_version.get("version_label", "")).lower())
            download_name = safe_stub or "lmsc-prospectus"
            if not download_name.endswith(".pdf"):
                download_name += ".pdf"

        structured_data_json: str | None = None
        if active_version is not None and document_url:
            structured_data = {
                "@context": "https://schema.org",
                "@type": "DigitalDocument",
                "name": active_version.get("version_label"),
                "description": active_version.get("description")
                or "London Maths & Science College prospectus",
                "fileFormat": "application/pdf",
                "url": document_url,
                "inLanguage": "en-GB",
                "publisher": {
                    "@type": "EducationalOrganization",
                    "name": "London Maths & Science College",
                    "url": request.url_root.rstrip("/"),
                },
            }
            if last_updated:
                structured_data["dateModified"] = last_updated
            structured_data_json = json.dumps(structured_data, separators=(",", ":"))

        return render_site_page(
            "prospectus.html",
            "prospectus",
            prospectus_version=active_version,
            prospectus_url=document_url,
            prospectus_last_updated=last_updated,
            prospectus_download_name=download_name,
            structured_data=structured_data_json,
        )

    @app.route("/pricing")
    def pricing() -> str:
        return render_site_page("pricing.html", "pricing")

    @app.route("/book-a-consultation", methods=["GET", "POST"])
    def book_consultation() -> str:
        form_data: dict[str, str] = {}
        timezone_default = "Europe/London"

        if request.method == "POST":
            form_data = request.form.to_dict()
            full_name = request.form.get("full_name", "").strip()
            email = request.form.get("email", "").strip()
            phone = request.form.get("phone", "").strip()
            student_name = request.form.get("student_name", "").strip()
            study_level = request.form.get("study_level", "").strip()
            interest_area = request.form.get("interest_area", "").strip()
            meeting_mode = request.form.get("meeting_mode", "").strip() or "Online"
            timezone_value = request.form.get("timezone", "").strip() or timezone_default
            selected_date = request.form.get("selected_date", "").strip()
            selected_time = request.form.get("selected_time", "").strip()
            notes = request.form.get("notes", "").strip()
            source = request.form.get("source") or request.path

            errors: list[str] = []
            if not full_name:
                errors.append("Please enter your full name so our team knows who to contact.")
            if not email:
                errors.append("Please add an email address so we can send a confirmation.")
            if not selected_date:
                errors.append("Pick a date for your consultation from the calendar.")
            if not selected_time:
                errors.append("Choose a time slot that works for you.")

            scheduled_at = None
            if selected_date and selected_time:
                try:
                    scheduled_dt = datetime.strptime(f"{selected_date} {selected_time}", "%Y-%m-%d %H:%M")
                    scheduled_at = scheduled_dt.strftime("%Y-%m-%d %H:%M:00")
                    if scheduled_dt < datetime.utcnow() - timedelta(minutes=30):
                        errors.append("That time has already passed. Please choose a future slot.")
                except ValueError:
                    errors.append("The selected date or time is invalid. Please pick another slot.")

            if errors:
                for message in errors:
                    flash(message, "error")
                return render_site_page(
                    "book_consultation.html",
                    "book-a-consultation",
                    form_data=form_data,
                    time_slots=CONSULTATION_TIME_SLOTS,
                    timezone_options=CONSULTATION_TIMEZONES,
                )

            booking_payload = {
                "full_name": full_name,
                "email": email,
                "phone": phone or None,
                "student_name": student_name or None,
                "study_level": study_level or None,
                "interest_area": interest_area or None,
                "meeting_mode": meeting_mode,
                "timezone": timezone_value,
                "scheduled_date": selected_date,
                "scheduled_time": selected_time,
                "scheduled_at": scheduled_at,
                "notes": notes or None,
                "status": "Pending",
                "source": source,
            }

            booking_id = create_consultation_booking(booking_payload)
            create_lead(
                "consultation",
                full_name=full_name,
                email=email,
                phone=phone or None,
                message=f"Consultation booked for {selected_date} at {selected_time}" if selected_date and selected_time else notes,
                source=source,
            )

            booking_row = get_consultation(booking_id)
            booking_dict = dict(booking_row) if booking_row is not None else booking_payload
            booking_dict.setdefault("id", booking_id)
            booking_dict.setdefault("status", "Pending")

            try:
                admin_url = url_for("admin_consultation_detail", consultation_id=booking_dict["id"], _external=True)
            except Exception:
                admin_url = None

            try:
                html_admin = render_template(
                    "emails/consultation_notification.html",
                    booking=booking_dict,
                    admin_url=admin_url,
                )
                app.send_email(
                    subject="New consultation booked",
                    recipients=[DEFAULT_ADMIN_USERNAME],
                    html=html_admin,
                )
            except Exception:
                pass

            try:
                html_client = render_template(
                    "emails/consultation_confirmation.html",
                    booking=booking_dict,
                    admin_email=DEFAULT_ADMIN_USERNAME,
                )
                app.send_email(
                    subject="Your LMSC consultation is booked",
                    recipients=[email],
                    html=html_client,
                )
            except Exception:
                pass

            flash("Thank you – your consultation request has been received. We will confirm shortly.", "success")
            return redirect(url_for("book_consultation"))

        if not form_data:
            form_data = {"timezone": timezone_default, "meeting_mode": "Online"}

        return render_site_page(
            "book_consultation.html",
            "book-a-consultation",
            form_data=form_data,
            time_slots=CONSULTATION_TIME_SLOTS,
            timezone_options=CONSULTATION_TIMEZONES,
        )

    @app.route("/blogs")
    def blogs() -> str:
        posts = fetch_blog_posts()
        return render_site_page(
            "blogs.html",
            "blogs",
            blog_posts=[dict(row) for row in posts],
        )

    @app.route("/blog-details")
    def blog_details() -> str:
        flash("Please choose an article from the blog list.", "info")
        return redirect(url_for("blogs"))

    @app.route("/blog/<slug>")
    def blog_post_detail(slug: str) -> str:
        post = get_blog_post_by_slug(slug)
        if post is None:
            flash("The requested article could not be found.", "error")
            return redirect(url_for("blogs"))

        post_dict = dict(post)
        page_meta = {
            "seo_title": f"{post_dict['title']} | LMSC Blog",
            "meta_description": post_dict.get("summary")
            or f"Read {post_dict['title']} on the LMSC blog.",
        }
        canonical_url = url_for("blog_post_detail", slug=slug, _external=True)
        encoded_url = quote_plus(canonical_url)
        share_text = post_dict.get("title") or "LMSC Blog"
        encoded_text = quote_plus(share_text)
        share_urls = {
            "facebook": f"https://www.facebook.com/sharer/sharer.php?u={encoded_url}",
            "x": f"https://twitter.com/intent/tweet?url={encoded_url}&text={encoded_text}",
            "linkedin": f"https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}",
            "email": f"mailto:?subject={encoded_text}&body={encoded_url}",
            "copy": canonical_url,
        }

        related_slugs = [post_dict.get(field) for field in BLOG_RELATION_FIELDS]
        related_posts = [
            dict(row) for row in fetch_related_blog_posts(related_slugs, exclude_id=int(post_dict["id"]))
        ]

        return render_template(
            "blog_details.html",
            post=post_dict,
            related_posts=related_posts,
            page_meta=page_meta,
            canonical_url=canonical_url,
            share_urls=share_urls,
        )

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

    @app.post("/analytics/track")
    def analytics_track():
        if not request.is_json:
            return ("", 204)

        origin = request.headers.get("Origin")
        if origin and not origin.startswith(request.host_url.rstrip("/")):
            return ("", 204)

        payload = request.get_json(silent=True) or {}
        path = str(payload.get("path") or "")
        if path.startswith("/admin"):
            return ("", 204)

        user_agent = request.headers.get("User-Agent", "")
        if is_probably_bot(user_agent):
            return ("", 204)

        url_value = payload.get("url")
        if not path and url_value:
            try:
                path = urlparse(url_value).path or ""
            except ValueError:
                path = ""

        referrer_value = payload.get("referrer") or request.referrer

        language = payload.get("language")
        visitor_id = payload.get("visitor_id")
        if not visitor_id:
            fallback_key = f"{request.headers.get('X-Forwarded-For', request.remote_addr)}|{user_agent}"
            visitor_id = hashlib.sha256(fallback_key.encode("utf-8", "ignore")).hexdigest()[:32]

        session_id = payload.get("session_id")
        if not session_id:
            session_hash_source = f"{visitor_id}|{payload.get('is_session_start')}|{current_timestamp()}"
            session_id = hashlib.sha256(session_hash_source.encode("utf-8", "ignore")).hexdigest()[:32]

        page_slug = payload.get("page_slug") or extract_slug_from_path(path)
        page_title = payload.get("page_title")

        traffic_source, utm_source, utm_medium, utm_campaign, referrer_domain = classify_traffic_source(
            url_value,
            referrer_value,
            request.host or "",
        )

        country = extract_country_from_headers(request, language)
        timezone = payload.get("timezone")
        screen_width = safe_int(payload.get("screen_width"))
        screen_height = safe_int(payload.get("screen_height"))
        is_session_start = 1 if payload.get("is_session_start") else 0

        device_type, device_os = detect_device_details(user_agent)

        db = get_db()
        db.execute(
            """
            INSERT INTO analytics_events (
                visitor_id,
                session_id,
                page_slug,
                page_title,
                path,
                url,
                referrer,
                referrer_domain,
                traffic_source,
                utm_source,
                utm_medium,
                utm_campaign,
                device_type,
                device_os,
                language,
                country,
                timezone,
                screen_width,
                screen_height,
                is_session_start,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                visitor_id,
                session_id,
                page_slug,
                page_title,
                path or None,
                url_value,
                referrer_value,
                referrer_domain,
                traffic_source,
                utm_source,
                utm_medium,
                utm_campaign,
                device_type,
                device_os,
                language,
                country,
                timezone,
                screen_width,
                screen_height,
                is_session_start,
                current_timestamp(),
            ),
        )
        db.commit()
        return ("", 204)

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

        total_consultations = db.execute(
            "SELECT COUNT(*) AS total FROM consultations"
        ).fetchone()["total"]
        upcoming_consultations_total = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM consultations
            WHERE scheduled_at IS NOT NULL
              AND datetime(scheduled_at) >= datetime('now')
            """
        ).fetchone()["total"]
        consultations_next_seven = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM consultations
            WHERE scheduled_at IS NOT NULL
              AND datetime(scheduled_at) BETWEEN datetime('now') AND datetime('now', '+7 day')
            """
        ).fetchone()["total"]
        consultations_today = db.execute(
            "SELECT COUNT(*) AS total FROM consultations WHERE scheduled_date = DATE('now', 'localtime')"
        ).fetchone()["total"]

        consultation_status_rows = db.execute(
            "SELECT status, COUNT(*) AS total FROM consultations GROUP BY status"
        ).fetchall()
        consultation_status_counts = {
            row["status"]: row["total"] for row in consultation_status_rows
        }

        upcoming_consultations = [dict(row) for row in fetch_upcoming_consultations(limit=6)]
        recent_consultations = [dict(row) for row in fetch_recent_consultations(limit=6)]

        kpis = {
            "total_leads": total_leads,
            "weekly_leads": weekly_leads,
            "subscription_count": subscription_count,
            "contact_count": contact_count,
            "conversion_rate": conversion_rate,
            "consultation_total": total_consultations,
            "consultations_upcoming": upcoming_consultations_total,
            "consultations_week": consultations_next_seven,
            "consultations_today": consultations_today,
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
            consultation_statuses=CONSULTATION_STATUSES,
            consultation_status_counts=consultation_status_counts,
            upcoming_consultations=upcoming_consultations,
            recent_consultations=recent_consultations,
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

    @app.route("/admin/consultations")
    @login_required
    def admin_consultations() -> str:
        db = get_db()
        status_filter = request.args.get("status", "").strip()
        view_filter = request.args.get("view", "all").strip().lower()
        valid_status = status_filter if status_filter in CONSULTATION_STATUSES else None
        upcoming_only = view_filter == "upcoming"

        consultation_rows = fetch_consultations(
            status=valid_status,
            upcoming_only=upcoming_only,
        )
        consultations = [dict(row) for row in consultation_rows]

        status_rows = db.execute(
            "SELECT status, COUNT(*) AS total FROM consultations GROUP BY status"
        ).fetchall()
        status_counts = {row["status"]: row["total"] for row in status_rows}

        total_consultations = db.execute(
            "SELECT COUNT(*) AS total FROM consultations"
        ).fetchone()["total"]
        upcoming_total = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM consultations
            WHERE scheduled_at IS NOT NULL
              AND datetime(scheduled_at) >= datetime('now')
            """
        ).fetchone()["total"]

        upcoming_preview = [dict(row) for row in fetch_upcoming_consultations(limit=5)]

        return render_template(
            "admin/consultations/index.html",
            consultations=consultations,
            statuses=CONSULTATION_STATUSES,
            status_counts=status_counts,
            selected_status=valid_status,
            view_filter=view_filter,
            totals={
                "total": total_consultations,
                "upcoming": upcoming_total,
            },
            upcoming_preview=upcoming_preview,
        )

    @app.route("/admin/consultations/<int:consultation_id>", methods=["GET", "POST"])
    @login_required
    def admin_consultation_detail(consultation_id: int) -> str:
        booking_row = get_consultation(consultation_id)
        if booking_row is None:
            flash("That consultation booking could not be found.", "error")
            return redirect(url_for("admin_consultations"))

        booking = dict(booking_row)

        if request.method == "POST":
            updates: dict[str, Any] = {}
            errors: list[str] = []

            new_status = request.form.get("status", "").strip()
            if new_status:
                if new_status in CONSULTATION_STATUSES:
                    if new_status != booking.get("status"):
                        updates["status"] = new_status
                else:
                    errors.append("Select a valid consultation status.")

            new_date = request.form.get("scheduled_date", "").strip()
            new_time = request.form.get("scheduled_time", "").strip()
            if new_date or new_time:
                if not new_date or not new_time:
                    errors.append("Provide both a date and time to reschedule the meeting.")
                else:
                    try:
                        scheduled_dt = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
                        updates["scheduled_date"] = new_date
                        updates["scheduled_time"] = new_time
                        updates["scheduled_at"] = scheduled_dt.strftime("%Y-%m-%d %H:%M:00")
                    except ValueError:
                        errors.append("The rescheduled date or time is invalid.")

            meeting_mode = request.form.get("meeting_mode", "").strip()
            if meeting_mode and meeting_mode != booking.get("meeting_mode"):
                updates["meeting_mode"] = meeting_mode

            timezone_value = request.form.get("timezone", "").strip()
            if timezone_value and timezone_value != booking.get("timezone"):
                updates["timezone"] = timezone_value

            notes = request.form.get("notes", "").strip()
            if notes != (booking.get("notes") or ""):
                updates["notes"] = notes or None

            if errors:
                for message in errors:
                    flash(message, "error")
            else:
                if updates:
                    update_consultation_fields(consultation_id, **updates)
                    flash("Consultation updated successfully.", "success")
                else:
                    flash("No changes were made to this consultation.", "info")
                return redirect(url_for("admin_consultation_detail", consultation_id=consultation_id))

        booking_row = get_consultation(consultation_id)
        booking = dict(booking_row) if booking_row is not None else booking

        return render_template(
            "admin/consultations/detail.html",
            booking=booking,
            statuses=CONSULTATION_STATUSES,
            timezone_options=CONSULTATION_TIMEZONES,
            time_slots=CONSULTATION_TIME_SLOTS,
        )

    @app.post("/admin/consultations/<int:consultation_id>/status")
    @login_required
    def admin_consultation_update_status(consultation_id: int):
        status_value = request.form.get("status", "").strip()
        if status_value not in CONSULTATION_STATUSES:
            flash("Please choose a valid status.", "error")
        else:
            update_consultation_status_db(consultation_id, status_value)
            flash("Consultation status updated.", "success")
        return redirect(request.referrer or url_for("admin_consultations"))

    @app.route("/admin/analytics")
    @login_required
    def admin_analytics() -> str:
        db = get_db()
        allowed_ranges = [7, 30, 60, 90, 180]
        try:
            range_days = int(request.args.get("range", "30"))
        except ValueError:
            range_days = 30
        if range_days not in allowed_ranges:
            range_days = 30

        current_range_label = f"-{range_days} day"
        previous_range_label = f"-{2 * range_days} day"
        comparison_label = f"vs previous {range_days} days"
        range_label = f"Last {range_days} days"

        totals = db.execute(
            """
            SELECT
                COUNT(*) AS page_views,
                COUNT(DISTINCT visitor_id) AS unique_visitors,
                COUNT(DISTINCT session_id) AS sessions
            FROM analytics_events
            WHERE datetime(created_at) >= datetime('now', ?)
            """,
            (current_range_label,),
        ).fetchone()

        previous_totals = db.execute(
            """
            SELECT
                COUNT(*) AS page_views,
                COUNT(DISTINCT visitor_id) AS unique_visitors,
                COUNT(DISTINCT session_id) AS sessions
            FROM analytics_events
            WHERE datetime(created_at) >= datetime('now', ?)
              AND datetime(created_at) < datetime('now', ?)
            """,
            (previous_range_label, current_range_label),
        ).fetchone()

        page_views = totals["page_views"] or 0
        unique_visitors = totals["unique_visitors"] or 0
        sessions = totals["sessions"] or 0

        prev_page_views = previous_totals["page_views"] or 0
        prev_unique_visitors = previous_totals["unique_visitors"] or 0
        prev_sessions = previous_totals["sessions"] or 0

        session_summary = db.execute(
            """
            SELECT
                SUM(CASE WHEN views = 1 THEN 1 ELSE 0 END) AS single_page_sessions,
                COUNT(*) AS total_sessions
            FROM (
                SELECT session_id, COUNT(*) AS views
                FROM analytics_events
                WHERE datetime(created_at) >= datetime('now', ?)
                GROUP BY session_id
            )
            """,
            (current_range_label,),
        ).fetchone()

        previous_session_summary = db.execute(
            """
            SELECT
                SUM(CASE WHEN views = 1 THEN 1 ELSE 0 END) AS single_page_sessions,
                COUNT(*) AS total_sessions
            FROM (
                SELECT session_id, COUNT(*) AS views
                FROM analytics_events
                WHERE datetime(created_at) >= datetime('now', ?)
                  AND datetime(created_at) < datetime('now', ?)
                GROUP BY session_id
            )
            """,
            (previous_range_label, current_range_label),
        ).fetchone()

        single_page_sessions = session_summary["single_page_sessions"] or 0
        total_sessions = session_summary["total_sessions"] or 0
        bounce_rate = round((single_page_sessions / total_sessions) * 100, 1) if total_sessions else 0.0

        prev_single_page_sessions = previous_session_summary["single_page_sessions"] or 0
        prev_total_sessions = previous_session_summary["total_sessions"] or 0
        prev_bounce_rate = (
            round((prev_single_page_sessions / prev_total_sessions) * 100, 1)
            if prev_total_sessions
            else 0.0
        )

        avg_pages_per_session = round(page_views / sessions, 2) if sessions else 0.0
        prev_avg_pages_per_session = round(prev_page_views / prev_sessions, 2) if prev_sessions else 0.0

        lead_row = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM leads
            WHERE datetime(created_at) >= datetime('now', ?)
            """,
            (current_range_label,),
        ).fetchone()
        lead_count = lead_row["total"] or 0
        conversion_rate = round((lead_count / sessions) * 100, 1) if sessions else 0.0

        prev_lead_row = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM leads
            WHERE datetime(created_at) >= datetime('now', ?)
              AND datetime(created_at) < datetime('now', ?)
            """,
            (previous_range_label, current_range_label),
        ).fetchone()
        prev_lead_count = prev_lead_row["total"] or 0
        prev_conversion_rate = (
            round((prev_lead_count / prev_sessions) * 100, 1)
            if prev_sessions
            else 0.0
        )

        new_visitors_row = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM (
                SELECT visitor_id, MIN(datetime(created_at)) AS first_seen
                FROM analytics_events
                GROUP BY visitor_id
                HAVING datetime(first_seen) >= datetime('now', ?)
            )
            """,
            (current_range_label,),
        ).fetchone()
        new_visitors = new_visitors_row["total"] or 0
        returning_visitors = max(unique_visitors - new_visitors, 0)
        new_visitor_rate = round((new_visitors / unique_visitors) * 100, 1) if unique_visitors else 0.0

        prev_new_visitors_row = db.execute(
            """
            SELECT COUNT(*) AS total
            FROM (
                SELECT visitor_id, MIN(datetime(created_at)) AS first_seen
                FROM analytics_events
                GROUP BY visitor_id
                HAVING datetime(first_seen) >= datetime('now', ?)
                  AND datetime(first_seen) < datetime('now', ?)
            )
            """,
            (previous_range_label, current_range_label),
        ).fetchone()
        prev_new_visitors = prev_new_visitors_row["total"] or 0
        prev_new_visitor_rate = (
            round((prev_new_visitors / prev_unique_visitors) * 100, 1)
            if prev_unique_visitors
            else 0.0
        )

        avg_daily_views = round(page_views / range_days, 1) if range_days else page_views
        prev_avg_daily_views = round(prev_page_views / range_days, 1) if range_days else prev_page_views

        def trend_direction(change: float | None) -> str:
            if change is None:
                return "neutral"
            if change > 0:
                return "up"
            if change < 0:
                return "down"
            return "neutral"

        def build_card(
            label: str,
            value: float | int,
            prev_value: float | int,
            value_format: str,
            *,
            invert: bool = False,
            supplement: str | None = None,
        ) -> dict[str, object]:
            change = compute_percent_change(value, prev_value)
            direction_basis = -change if (change is not None and invert) else change
            return {
                "label": label,
                "value": value,
                "trend": change,
                "trend_direction": trend_direction(direction_basis),
                "caption": comparison_label,
                "format": value_format,
                "supplement": supplement,
            }

        kpi_cards = [
            build_card("Page Views", page_views, prev_page_views, "number"),
            build_card("Sessions", sessions, prev_sessions, "number"),
            build_card("Unique Visitors", unique_visitors, prev_unique_visitors, "number"),
            build_card("Bounce Rate", bounce_rate, prev_bounce_rate, "percent", invert=True),
            build_card("Pages / Session", avg_pages_per_session, prev_avg_pages_per_session, "decimal"),
            build_card("Lead Conversion", conversion_rate, prev_conversion_rate, "percent"),
            build_card(
                "New Visitor Share",
                new_visitor_rate,
                prev_new_visitor_rate,
                "percent",
                supplement=f"{new_visitors:,} new / {unique_visitors:,} unique",
            ),
            build_card("Avg Daily Views", avg_daily_views, prev_avg_daily_views, "decimal"),
        ]

        daily_rows = db.execute(
            """
            SELECT DATE(created_at) AS day,
                   COUNT(*) AS page_views,
                   COUNT(DISTINCT session_id) AS sessions,
                   COUNT(DISTINCT visitor_id) AS unique_visitors
            FROM analytics_events
            WHERE datetime(created_at) >= datetime('now', ?)
            GROUP BY day
            ORDER BY day
            """,
            (current_range_label,),
        ).fetchall()

        day_map = {row["day"]: row for row in daily_rows}
        day_labels: list[str] = []
        page_views_series: list[int] = []
        sessions_series: list[int] = []
        unique_series: list[int] = []
        now_utc = datetime.utcnow()
        for offset in range(range_days - 1, -1, -1):
            day_point = now_utc - timedelta(days=offset)
            day_key = day_point.strftime("%Y-%m-%d")
            day_labels.append(day_point.strftime("%d %b"))
            row = day_map.get(day_key)
            if row:
                page_views_series.append(row["page_views"] or 0)
                sessions_series.append(row["sessions"] or 0)
                unique_series.append(row["unique_visitors"] or 0)
            else:
                page_views_series.append(0)
                sessions_series.append(0)
                unique_series.append(0)

        daily_chart = {
            "labels": day_labels,
            "page_views": page_views_series,
            "sessions": sessions_series,
            "unique": unique_series,
        }

        hourly_rows = db.execute(
            """
            SELECT STRFTIME('%H', created_at) AS hour,
                   COUNT(*) AS visits
            FROM analytics_events
            WHERE datetime(created_at) >= datetime('now', ?)
            GROUP BY hour
            ORDER BY hour
            """,
            (current_range_label,),
        ).fetchall()
        hour_map = {row["hour"]: row["visits"] for row in hourly_rows}
        hourly_labels = [f"{hour:02d}:00" for hour in range(24)]
        hourly_values = [hour_map.get(f"{hour:02d}", 0) for hour in range(24)]
        hourly_chart = {"labels": hourly_labels, "values": hourly_values}

        device_rows = db.execute(
            """
            SELECT COALESCE(NULLIF(device_type, ''), 'Unknown') AS device_type,
                   COUNT(*) AS visits
            FROM analytics_events
            WHERE datetime(created_at) >= datetime('now', ?)
            GROUP BY device_type
            ORDER BY visits DESC
            """,
            (current_range_label,),
        ).fetchall()
        device_chart = {
            "labels": [row["device_type"] for row in device_rows],
            "values": [row["visits"] for row in device_rows],
        }

        os_rows = db.execute(
            """
            SELECT COALESCE(NULLIF(device_os, ''), 'Other') AS device_os,
                   COUNT(*) AS visits
            FROM analytics_events
            WHERE datetime(created_at) >= datetime('now', ?)
            GROUP BY device_os
            ORDER BY visits DESC
            """,
            (current_range_label,),
        ).fetchall()

        traffic_rows = db.execute(
            """
            SELECT COALESCE(NULLIF(traffic_source, ''), 'Direct') AS traffic_source,
                   COUNT(*) AS visits
            FROM analytics_events
            WHERE datetime(created_at) >= datetime('now', ?)
            GROUP BY traffic_source
            ORDER BY visits DESC
            """,
            (current_range_label,),
        ).fetchall()
        traffic_chart = {
            "labels": [row["traffic_source"] for row in traffic_rows],
            "values": [row["visits"] for row in traffic_rows],
        }

        country_rows = db.execute(
            """
            SELECT COALESCE(NULLIF(country, ''), 'Unknown') AS country,
                   COUNT(*) AS visits,
                   COUNT(DISTINCT visitor_id) AS unique_visitors
            FROM analytics_events
            WHERE datetime(created_at) >= datetime('now', ?)
            GROUP BY country
            ORDER BY visits DESC
            LIMIT 10
            """,
            (current_range_label,),
        ).fetchall()
        country_chart = {
            "labels": [row["country"] for row in country_rows[:6]],
            "values": [row["visits"] for row in country_rows[:6]],
        }

        referrer_rows = db.execute(
            """
            SELECT
                COALESCE(NULLIF(referrer_domain, ''), traffic_source) AS domain,
                traffic_source,
                COUNT(*) AS visits
            FROM analytics_events
            WHERE datetime(created_at) >= datetime('now', ?)
            GROUP BY domain, traffic_source
            ORDER BY visits DESC
            LIMIT 10
            """,
            (current_range_label,),
        ).fetchall()

        timezone_rows = db.execute(
            """
            SELECT COALESCE(NULLIF(timezone, ''), 'Unknown') AS timezone,
                   COUNT(*) AS visits
            FROM analytics_events
            WHERE datetime(created_at) >= datetime('now', ?)
            GROUP BY timezone
            ORDER BY visits DESC
            LIMIT 8
            """,
            (current_range_label,),
        ).fetchall()

        page_lookup = {row["slug"]: row for row in fetch_all_pages()}
        top_pages_rows = db.execute(
            """
            SELECT
                page_slug,
                COALESCE(NULLIF(page_title, ''), NULL) AS page_title,
                path,
                COUNT(*) AS views,
                COUNT(DISTINCT session_id) AS sessions
            FROM analytics_events
            WHERE datetime(created_at) >= datetime('now', ?)
            GROUP BY page_slug, page_title, path
            ORDER BY views DESC
            LIMIT 10
            """,
            (current_range_label,),
        ).fetchall()

        def resolve_public_url(slug: str | None, path_value: str | None) -> str:
            if slug:
                endpoint = PAGE_ENDPOINT_OVERRIDES.get(slug)
                if endpoint:
                    try:
                        return url_for(endpoint)
                    except Exception:
                        pass
                try:
                    return url_for("render_dynamic_page", slug=slug)
                except Exception:
                    pass
            if path_value:
                return path_value
            return "#"

        top_pages: list[dict[str, object]] = []
        for row in top_pages_rows:
            slug = row["page_slug"]
            page_title = row["page_title"]
            page_record = page_lookup.get(slug) if slug else None
            display_name = (
                page_title
                or (page_record["page_name"] if page_record else None)
                or (slug.capitalize() if slug else (row["path"] or "Unknown"))
            )
            share = round((row["views"] / page_views) * 100, 1) if page_views else 0.0
            top_pages.append(
                {
                    "title": display_name,
                    "slug": slug,
                    "views": row["views"],
                    "sessions": row["sessions"],
                    "share": share,
                    "url": resolve_public_url(slug, row["path"]),
                }
            )

        top_countries = [
            {
                "country": row["country"],
                "visits": row["visits"],
                "unique": row["unique_visitors"],
                "share": round((row["visits"] / page_views) * 100, 1) if page_views else 0.0,
            }
            for row in country_rows
        ]

        referrer_table = [
            {
                "domain": row["domain"],
                "visits": row["visits"],
                "source": row["traffic_source"],
            }
            for row in referrer_rows
        ]

        timezone_table = [
            {
                "timezone": row["timezone"],
                "visits": row["visits"],
            }
            for row in timezone_rows
        ]

        device_table = [
            {
                "device_type": row["device_type"],
                "visits": row["visits"],
                "share": round((row["visits"] / page_views) * 100, 1) if page_views else 0.0,
            }
            for row in device_rows
        ]

        os_table = [
            {
                "device_os": row["device_os"],
                "visits": row["visits"],
                "share": round((row["visits"] / page_views) * 100, 1) if page_views else 0.0,
            }
            for row in os_rows
        ]

        traffic_table = [
            {
                "source": row["traffic_source"],
                "visits": row["visits"],
                "share": round((row["visits"] / page_views) * 100, 1) if page_views else 0.0,
            }
            for row in traffic_rows
        ]

        context = {
            "range_days": range_days,
            "range_label": range_label,
            "comparison_label": comparison_label,
            "range_options": allowed_ranges,
            "kpi_cards": kpi_cards,
            "daily_chart": daily_chart,
            "hourly_chart": hourly_chart,
            "device_chart": device_chart,
            "traffic_chart": traffic_chart,
            "country_chart": country_chart,
            "top_pages": top_pages,
            "top_countries": top_countries,
            "referrer_table": referrer_table,
            "timezone_table": timezone_table,
            "device_table": device_table,
            "os_table": os_table,
            "traffic_table": traffic_table,
            "lead_count": lead_count,
            "returning_visitors": returning_visitors,
            "new_visitors": new_visitors,
            "new_visitor_rate": new_visitor_rate,
            "conversion_rate": conversion_rate,
            "page_views": page_views,
            "sessions_total": sessions,
            "unique_visitors": unique_visitors,
            "bounce_rate": bounce_rate,
            "avg_pages_per_session": avg_pages_per_session,
        }

        return render_template("admin/analytics.html", **context)

    @app.route("/admin/pages")
    @login_required
    def admin_pages() -> str:
        pages = fetch_all_pages()
        parent_lookup = {page["id"]: page["page_name"] for page in pages}
        nav_counts: dict[str, int] = {"main": 0, "dropdown": 0, "footer": 0, "hidden": 0}
        meta_missing_ids: set[int] = set()

        for page in pages:
            display = page["nav_display"] or "hidden"
            nav_counts[display] = nav_counts.get(display, 0) + 1
            if not page["seo_title"] or not page["meta_description"]:
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

        def page_admin_url(page_row: sqlite3.Row) -> str:
            endpoint = PAGE_ENDPOINT_OVERRIDES.get(page_row["slug"])
            if endpoint:
                try:
                    return url_for(endpoint)
                except Exception:
                    pass
            return url_for("render_dynamic_page", slug=page_row["slug"])

        page_urls = {page["id"]: page_admin_url(page) for page in pages}

        return render_template(
            "admin/pages/index.html",
            pages=pages,
            parent_lookup=parent_lookup,
            nav_stats=stats,
            meta_gaps=meta_missing_ids,
            page_urls=page_urls,
        )

    @app.route("/admin/blogs")
    @login_required
    def admin_blogs() -> str:
        posts = fetch_blog_posts()
        total_posts = len(posts)
        latest_publish = posts[0]["publish_date"] if posts else None
        last_updated = max((row["updated_at"] for row in posts), default=None) if posts else None
        stats = {
            "total": total_posts,
            "latest_publish": latest_publish,
            "last_updated": last_updated,
        }
        return render_template(
            "admin/blogs/index.html",
            posts=posts,
            stats=stats,
        )

    @app.route("/admin/blogs/new", methods=["GET", "POST"])
    @login_required
    def admin_blogs_new() -> str:
        related_options = fetch_blog_posts()
        if request.method == "POST":
            data, errors, notices = collect_blog_payload()
            if not errors:
                image_errors = process_blog_images(data, require_primary=True)
                errors.extend(image_errors)

            if errors:
                for message in errors:
                    flash(message, "error")
                for note in notices:
                    flash(note, "info")
                form_snapshot = request.form.to_dict()
                return render_template(
                    "admin/blogs/form.html",
                    mode="create",
                    form_data=form_snapshot,
                    draft_data=data,
                    related_options=related_options,
                    post_data=None,
                )

            create_blog_post(data)
            flash("Blog article created successfully.", "success")
            for note in notices:
                flash(note, "info")
            return redirect(url_for("admin_blogs"))

        default_date = datetime.utcnow().strftime("%Y-%m-%d")
        form_data = {"publish_date": default_date}
        return render_template(
            "admin/blogs/form.html",
            mode="create",
            form_data=form_data,
            draft_data=None,
            related_options=related_options,
            post_data=None,
        )

    @app.route("/admin/blogs/<int:post_id>/edit", methods=["GET", "POST"])
    @login_required
    def admin_blogs_edit(post_id: int) -> str:
        post = get_blog_post(post_id)
        if post is None:
            flash("Blog article not found.", "error")
            return redirect(url_for("admin_blogs"))

        post_dict = dict(post)
        related_options = [row for row in fetch_blog_posts() if int(row["id"]) != post_id]

        if request.method == "POST":
            data, errors, notices = collect_blog_payload(post)
            if not errors:
                image_errors = process_blog_images(data, existing=post, require_primary=True)
                errors.extend(image_errors)

            if errors:
                for message in errors:
                    flash(message, "error")
                for note in notices:
                    flash(note, "info")
                form_snapshot = request.form.to_dict()
                return render_template(
                    "admin/blogs/form.html",
                    mode="edit",
                    form_data=form_snapshot,
                    draft_data=data,
                    related_options=related_options,
                    post_data=post_dict,
                )

            update_blog_post(post_id, data)
            flash("Blog article updated successfully.", "success")
            for note in notices:
                flash(note, "info")
            return redirect(url_for("admin_blogs"))

        form_data = dict(post)
        return render_template(
            "admin/blogs/form.html",
            mode="edit",
            form_data=form_data,
            draft_data=None,
            related_options=related_options,
            post_data=post_dict,
        )

    @app.post("/admin/blogs/<int:post_id>/delete")
    @login_required
    def admin_blogs_delete(post_id: int) -> str:
        post = get_blog_post(post_id)
        if post is None:
            flash("Blog article not found.", "error")
            return redirect(url_for("admin_blogs"))

        post_dict = dict(post)
        for path_column, _, _ in BLOG_IMAGE_FIELD_MAP.values():
            remove_static_file(post_dict.get(path_column))

        delete_blog_post(post_id)
        flash("Blog article removed.", "info")
        return redirect(url_for("admin_blogs"))

    @app.route("/admin/courses")
    @login_required
    def admin_courses() -> str:
        courses = fetch_courses()
        stats = fetch_course_stats()
        return render_template(
            "admin/courses/index.html",
            courses=courses,
            stats=stats,
        )

    @app.route("/admin/courses/new", methods=["GET", "POST"])
    @login_required
    def admin_courses_new() -> str:
        if request.method == "POST":
            data, errors, notices, faq_items, list_values = collect_course_payload()
            upload = request.files.get("image")
            pending_image_path: str | None = None

            remove_flag = request.form.get("remove_image") == "on"
            if remove_flag:
                data["image_path"] = None
                data["image_alt"] = None

            if upload and upload.filename:
                if not data.get("image_alt"):
                    errors.append("Please provide alt text for the course card image.")
                if not errors:
                    try:
                        pending_image_path = save_course_image(upload)
                        data["image_path"] = pending_image_path
                    except ValueError as exc:
                        errors.append(str(exc))

            if data.get("image_path") and not data.get("image_alt"):
                errors.append("Please provide alt text for the course card image.")

            if errors:
                if pending_image_path:
                    remove_static_file(pending_image_path)
                for message in errors:
                    flash(message, "error")
                form_snapshot = request.form.to_dict()
                return render_template(
                    "admin/courses/form.html",
                    mode="create",
                    form_data=form_snapshot,
                    course_data=None,
                    faq_items=faq_items,
                    list_values=list_values,
                    related_course_options=build_related_course_options(),
                )

            course_id = create_course(data)
            replace_course_faqs(course_id, faq_items)
            flash("Course created successfully.", "success")
            for note in notices:
                flash(note, "info")
            return redirect(url_for("admin_courses"))

        existing_courses = fetch_courses()
        suggested_order = 1
        if existing_courses:
            last_display = existing_courses[-1]["display_order"]
            try:
                suggested_order = int(last_display) + 1
            except (TypeError, ValueError):
                suggested_order = len(existing_courses) + 1

        form_defaults = {"display_order": suggested_order}
        list_defaults = {
            "study_topics": [],
            "skills_built": [],
            "audience_notes": [],
            "includes_items": [],
            "faq_items": [],
        }
        return render_template(
            "admin/courses/form.html",
            mode="create",
            form_data=form_defaults,
            course_data=None,
            faq_items=[],
            list_values=list_defaults,
            related_course_options=build_related_course_options(),
        )

    @app.route("/admin/courses/<int:course_id>/edit", methods=["GET", "POST"])
    @login_required
    def admin_courses_edit(course_id: int) -> str:
        course = get_course_by_id(course_id)
        if course is None:
            flash("Course not found.", "error")
            return redirect(url_for("admin_courses"))

        course_dict = dict(course)
        existing_faqs = [dict(row) for row in fetch_course_faqs(course_id)]
        existing_lists = {
            "study_topics": split_multiline(course_dict.get("study_topics")),
            "skills_built": split_multiline(course_dict.get("skills_built")),
            "audience_notes": split_multiline(course_dict.get("audience_notes")),
            "includes_items": split_multiline(course_dict.get("includes_items")),
            "faq_items": existing_faqs,
        }

        if request.method == "POST":
            data, errors, notices, faq_items, list_values = collect_course_payload(course)
            upload = request.files.get("image")
            pending_image_path: str | None = None
            remove_existing_image = False

            if upload and upload.filename:
                if not data.get("image_alt"):
                    errors.append("Please provide alt text for the course card image.")
                if not errors:
                    try:
                        pending_image_path = save_course_image(upload)
                        data["image_path"] = pending_image_path
                    except ValueError as exc:
                        errors.append(str(exc))
            elif request.form.get("remove_image") == "on":
                data["image_path"] = None
                data["image_alt"] = None
                remove_existing_image = bool(course_dict.get("image_path"))
            else:
                data["image_path"] = course_dict.get("image_path")

            if data.get("image_path") and not data.get("image_alt"):
                errors.append("Please provide alt text for the course card image.")

            if errors:
                if pending_image_path:
                    remove_static_file(pending_image_path)
                for message in errors:
                    flash(message, "error")
                form_snapshot = request.form.to_dict()
                return render_template(
                    "admin/courses/form.html",
                    mode="edit",
                    form_data=form_snapshot,
                    course_data=course_dict,
                    faq_items=faq_items,
                    list_values=list_values,
                    related_course_options=build_related_course_options(exclude_id=course_id),
                )

            update_course(course_id, data)
            old_path = course_dict.get("image_path")
            if pending_image_path and old_path and old_path != pending_image_path:
                remove_static_file(old_path)
            elif remove_existing_image and old_path:
                remove_static_file(old_path)

            replace_course_faqs(course_id, faq_items)
            flash("Course updated successfully.", "success")
            for note in notices:
                flash(note, "info")
            return redirect(url_for("admin_courses"))

        return render_template(
            "admin/courses/form.html",
            mode="edit",
            form_data=course_dict,
            course_data=course_dict,
            faq_items=existing_faqs,
            list_values=existing_lists,
            related_course_options=build_related_course_options(exclude_id=course_id),
        )

    @app.post("/admin/courses/<int:course_id>/delete")
    @login_required
    def admin_courses_delete(course_id: int) -> str:
        course = get_course_by_id(course_id)
        if course is None:
            flash("Course not found.", "error")
            return redirect(url_for("admin_courses"))

        delete_course(course_id)
        flash("Course removed.", "info")
        return redirect(url_for("admin_courses"))

    @app.route("/admin/carousel")
    @login_required
    def admin_carousel() -> str:
        slides = fetch_carousel_slides(include_inactive=True)
        stats = fetch_carousel_stats()
        return render_template(
            "admin/carousel/index.html",
            slides=slides,
            stats=stats,
        )

    @app.route("/admin/carousel/new", methods=["GET", "POST"])
    @login_required
    def admin_carousel_new() -> str:
        if request.method == "POST":
            data, errors = collect_carousel_payload()
            upload = request.files.get("image")
            pending_image_path: str | None = None

            if upload and upload.filename:
                try:
                    pending_image_path = save_carousel_image(upload)
                    data["image_path"] = pending_image_path
                except ValueError as exc:
                    errors.append(str(exc))
            else:
                data["image_path"] = None

            if data.get("image_path"):
                if not data.get("image_alt"):
                    errors.append("Please provide alt text for the slide image.")
            else:
                data["image_alt"] = None

            if errors:
                if pending_image_path:
                    remove_static_file(pending_image_path)
                for message in errors:
                    flash(message, "error")
                form_snapshot = request.form.to_dict()
                form_snapshot["is_active"] = "on" if request.form.get("is_active") == "on" else ""
                return render_template(
                    "admin/carousel/form.html",
                    mode="create",
                    form_data=form_snapshot,
                    slide=None,
                )

            slide_id = create_carousel_slide(data)
            flash("Carousel slide created successfully.", "success")
            return redirect(url_for("admin_carousel_edit", slide_id=slide_id))

        slides = fetch_carousel_slides(include_inactive=True)
        existing_orders: list[int] = []
        for row in slides:
            value = row["display_order"]
            if value is None:
                continue
            try:
                existing_orders.append(int(value))
            except (TypeError, ValueError):
                continue
        suggested_order = max(existing_orders) + 1 if existing_orders else 1
        form_defaults = {"display_order": str(suggested_order), "is_active": "on"}
        return render_template(
            "admin/carousel/form.html",
            mode="create",
            form_data=form_defaults,
            slide=None,
        )

    @app.route("/admin/carousel/<int:slide_id>/edit", methods=["GET", "POST"])
    @login_required
    def admin_carousel_edit(slide_id: int) -> str:
        slide = get_carousel_slide(slide_id)
        if slide is None:
            flash("Carousel slide not found.", "error")
            return redirect(url_for("admin_carousel"))

        slide_dict = dict(slide)

        if request.method == "POST":
            data, errors = collect_carousel_payload(slide)
            upload = request.files.get("image")
            pending_image_path: str | None = None
            remove_existing = request.form.get("remove_image") == "on"

            if upload and upload.filename:
                try:
                    pending_image_path = save_carousel_image(upload)
                    data["image_path"] = pending_image_path
                except ValueError as exc:
                    errors.append(str(exc))
            elif remove_existing:
                data["image_path"] = None
            else:
                data["image_path"] = slide_dict.get("image_path")

            if data.get("image_path"):
                if not data.get("image_alt"):
                    errors.append("Please provide alt text for the slide image.")
            else:
                data["image_alt"] = None

            if errors:
                if pending_image_path:
                    remove_static_file(pending_image_path)
                for message in errors:
                    flash(message, "error")
                form_snapshot = request.form.to_dict()
                form_snapshot["is_active"] = "on" if request.form.get("is_active") == "on" else ""
                if remove_existing:
                    form_snapshot["remove_image"] = "on"
                return render_template(
                    "admin/carousel/form.html",
                    mode="edit",
                    form_data=form_snapshot,
                    slide=slide_dict,
                )

            update_carousel_slide(slide_id, data)
            old_path = slide_dict.get("image_path")
            if pending_image_path and old_path and old_path != pending_image_path:
                if isinstance(old_path, str) and old_path.startswith("uploads/"):
                    remove_static_file(old_path)
            elif remove_existing and old_path and isinstance(old_path, str) and old_path.startswith("uploads/"):
                remove_static_file(old_path)

            flash("Carousel slide updated successfully.", "success")
            return redirect(url_for("admin_carousel_edit", slide_id=slide_id))

        return render_template(
            "admin/carousel/form.html",
            mode="edit",
            form_data=slide_dict,
            slide=slide_dict,
        )

    @app.post("/admin/carousel/<int:slide_id>/delete")
    @login_required
    def admin_carousel_delete(slide_id: int) -> str:
        slide = get_carousel_slide(slide_id)
        if slide is None:
            flash("Carousel slide not found.", "error")
        else:
            delete_carousel_slide(slide_id)
            flash("Carousel slide removed.", "info")
        return redirect(url_for("admin_carousel"))

    @app.route("/admin/prospectus", methods=["GET", "POST"])
    @login_required
    def admin_prospectus() -> str:
        if request.method == "POST":
            pdf_file = request.files.get("document")
            version_label = request.form.get("version_label", "").strip()
            description = request.form.get("description", "").strip()
            activate_now = request.form.get("activate_now") == "on"

            try:
                document_path = save_prospectus_pdf(pdf_file)
            except ValueError as exc:
                flash(str(exc), "error")
                return redirect(url_for("admin_prospectus"))

            if not version_label:
                version_label = f"Prospectus {datetime.utcnow():%Y-%m-%d}"

            create_prospectus_version(
                version_label=version_label,
                description=description or None,
                document_path=document_path,
                activate_now=activate_now,
            )

            if activate_now:
                flash("New prospectus uploaded and set as active.", "success")
            else:
                flash("Prospectus version uploaded.", "success")

            return redirect(url_for("admin_prospectus"))

        versions = fetch_prospectus_versions()
        active_version = get_active_prospectus_version()
        active_id = int(active_version["id"]) if active_version is not None else None
        return render_template(
            "admin/prospectus.html",
            versions=versions,
            active_id=active_id,
        )

    @app.post("/admin/prospectus/<int:version_id>/activate")
    @login_required
    def admin_prospectus_activate(version_id: int):
        if set_active_prospectus_version(version_id):
            flash("Prospectus version activated.", "success")
        else:
            flash("Prospectus version not found.", "error")
        return redirect(url_for("admin_prospectus"))

    @app.post("/admin/prospectus/<int:version_id>/delete")
    @login_required
    def admin_prospectus_delete(version_id: int):
        version = get_prospectus_version(version_id)
        if version is None:
            flash("Prospectus version not found.", "error")
            return redirect(url_for("admin_prospectus"))

        db = get_db()
        fallback_id: int | None = None
        if version["is_active"]:
            fallback_row = db.execute(
                """
                SELECT id FROM prospectus_versions
                WHERE id != ?
                ORDER BY datetime(created_at) DESC, id DESC
                LIMIT 1
                """,
                (version_id,)
            ).fetchone()
            if fallback_row is not None:
                fallback_id = int(fallback_row["id"])

        remove_static_file(version["document_path"])
        delete_prospectus_version(version_id)

        if fallback_id is not None:
            set_active_prospectus_version(fallback_id)

        flash("Prospectus version deleted.", "info")
        return redirect(url_for("admin_prospectus"))

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

    def build_nav_parent_choices(
        *, exclude_id: int | None = None, include_parent_id: int | None = None
    ) -> list[sqlite3.Row]:
        pages = fetch_all_pages()
        choices: list[sqlite3.Row] = []
        fallback_parent: sqlite3.Row | None = None

        for page in pages:
            if exclude_id is not None and page["id"] == exclude_id:
                continue

            is_top_level = page["nav_parent_id"] is None
            if is_top_level:
                choices.append(page)
            elif include_parent_id is not None and page["id"] == include_parent_id:
                fallback_parent = page

        if include_parent_id is not None and all(
            choice["id"] != include_parent_id for choice in choices
        ):
            if fallback_parent is not None:
                choices.append(fallback_parent)

        choices.sort(key=lambda row: (row["nav_order"], row["page_name"]))
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
        parent_choices = build_nav_parent_choices(
            exclude_id=page_id, include_parent_id=page["nav_parent_id"]
        )

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
        page_name = page_dict.get("page_name")
        if page_name and not page_dict.get("seo_title"):
            page_dict["seo_title"] = f"{page_name} | London Maths & Science College"
        if page_name and not page_dict.get("meta_description"):
            page_dict["meta_description"] = (
                f"Learn more about {page_name} at London Maths & Science College."
            )
        template_name = page_dict["template_name"]

        try:
            canonical_url = build_canonical_url(slug)
        except Exception:
            canonical_url = request.base_url

        robots_meta = page_dict.get("meta_robots")
        if not robots_meta and should_noindex(slug):
            robots_meta = "noindex, nofollow"

        return render_template(
            template_name,
            page=page_dict,
            page_meta=page_dict,
            canonical_url=canonical_url,
            meta_robots=robots_meta,
        )

    @app.cli.command("process-images")
    @click.option("--sizes", default=None, help="Comma-separated list of widths")
    @click.option("--quality", default=85, type=int, show_default=True, help="Fallback JPEG quality")
    @click.option("--webp-quality", default=80, type=int, show_default=True, help="WebP quality")
    @click.option("--avif-quality", default=45, type=int, show_default=True, help="AVIF quality")
    @click.option("--overwrite", is_flag=True, help="Overwrite existing derivatives")
    def process_images_command(**options):
        """Expose the responsive image pipeline via ``flask process-images``."""

        argv: list[str] = []
        if options["sizes"]:
            argv.extend(["--sizes", options["sizes"]])
        if options["quality"] != 85:
            argv.extend(["--quality", str(options["quality"])])
        if options["webp_quality"] != 80:
            argv.extend(["--webp-quality", str(options["webp_quality"])])
        if options["avif_quality"] != 45:
            argv.extend(["--avif-quality", str(options["avif_quality"])])
        if options["overwrite"]:
            argv.append("--overwrite")

        process_images_module.main(argv)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
