import { animate } from "https://cdn.jsdelivr.net/npm/motion@11.16.0/+esm";

const menuToggle = document.getElementById("menuToggle");
const closeMenu = document.getElementById("closeMenu");
const offcanvasMenu = document.getElementById("offcanvasMenu");
const offcanvasOverlay = document.getElementById("offcanvasOverlay");
const body = document.body;

const openMenu = () => {
    if (!offcanvasMenu || !offcanvasOverlay || !menuToggle) {
        return;
    }
    offcanvasMenu.classList.add("active");
    offcanvasOverlay.classList.add("active");
    menuToggle.classList.add("active");
    body.classList.add("menu-open");
};

const closeMenuFunc = () => {
    if (!offcanvasMenu || !offcanvasOverlay || !menuToggle) {
        return;
    }
    offcanvasMenu.classList.remove("active");
    offcanvasOverlay.classList.remove("active");
    menuToggle.classList.remove("active");
    body.classList.remove("menu-open");
};

if (menuToggle && closeMenu && offcanvasMenu && offcanvasOverlay) {
    menuToggle.addEventListener("click", openMenu);
    closeMenu.addEventListener("click", closeMenuFunc);
    offcanvasOverlay.addEventListener("click", closeMenuFunc);

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && offcanvasMenu.classList.contains("active")) {
            closeMenuFunc();
        }
    });

    window.addEventListener("resize", () => {
        if (window.innerWidth >= 1024 && offcanvasMenu.classList.contains("active")) {
            closeMenuFunc();
        }
    });
}

const toggleSubmenu = (id) => {
    const submenu = document.getElementById(`${id}-submenu`);
    const icon = document.getElementById(`${id}-icon`);

    if (!submenu || !icon) {
        return;
    }

    submenu.classList.toggle("active");
    icon.style.transform = submenu.classList.contains("active") ? "rotate(180deg)" : "rotate(0deg)";
};

const images = {
    "why-lmsc": "https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=800",
    "stem-pathways": "https://images.unsplash.com/photo-1523580494863-6f3031224c94?w=800",
    "study-options": "https://images.unsplash.com/photo-1554774853-b415df9eeb92?w=800",
    "fees-finance": "https://images.unsplash.com/photo-1563013544-824ae1b704d3",
    "open-events": "https://images.unsplash.com/photo-1523580494863-6f3031224c94?w=800",
    prospectus: "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=800",
    "teach-stem": "https://images.unsplash.com/photo-1523580494863-6f3031224c94?w=800",
    teachers: "https://images.unsplash.com/photo-1523580494863-6f3031224c94?w=800",
    "evidence-teaching": "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=800",
    "learning-support": "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=800",
    "send-support": "https://images.unsplash.com/photo-1526925539332-aa3b66e35444?w=800",
    "digital-learning": "https://images.unsplash.com/photo-1587620962725-abab7fe55159?w=800",
    facilities: "https://images.unsplash.com/photo-1496307042754-b4aa456c4a2d?w=800",
    research: "https://images.unsplash.com/photo-1521791055366-0d553872125f?w=800",
    "exam-info": "https://images.unsplash.com/photo-1496307042754-b4aa456c4a2d?w=800",
    "life-lmsc": "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=800",
    "student-community": "https://images.unsplash.com/photo-1496307042754-b4aa456c4a2d?w=800",
    "pastoral-care": "https://images.unsplash.com/photo-1521747116042-5a810fda9664?w=800",
    "tutor-system": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=800",
    inclusion: "https://images.unsplash.com/photo-1496307042754-b4aa456c4a2d?w=800",
    sphere: "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=800",
    faith: "https://images.unsplash.com/photo-1521747116042-5a810fda9664?w=800",
    assemblies: "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=800",
    "summer-camps": "https://images.unsplash.com/photo-1496307042754-b4aa456c4a2d?w=800",
    "online-programmes": "https://images.unsplash.com/photo-1588196749597-9ff075ee6b5b?w=800",
    "homeschool-advice": "https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=800",
    "computer-req": "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=800",
    "it-support": "https://images.unsplash.com/photo-1587620962725-abab7fe55159?w=800",
    faqs: "https://images.unsplash.com/photo-1522202176988-66273c2fd55f",
    careers: "https://images.unsplash.com/photo-1503676260728-1c00da094a0b",
    "study-guidance": "https://images.unsplash.com/photo-1513258496099-48168024aec0",
    "exam-policies": "https://images.unsplash.com/photo-1509223197845-458d87318791",
    "payment-plans": "https://images.unsplash.com/photo-1563013544-824ae1b704d3",
    blog: "https://images.unsplash.com/photo-1515378791036-0648a3ef77b2",
    mission: "https://images.unsplash.com/photo-1454165205744-3b78555e5572",
    vision: "https://images.unsplash.com/photo-1503676260728-1c00da094a0b",
    principal: "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d",
    governance: "https://images.unsplash.com/photo-1519681393784-d120267933ba",
    partnerships: "https://images.unsplash.com/photo-1521791136064-7986c2920216",
    history: "https://images.unsplash.com/photo-1519681393784-d120267933ba",
    "learning-space": "https://images.unsplash.com/photo-1509223197845-458d87318791",
    alumni: "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f",
    reports: "https://images.unsplash.com/photo-1554224155-6726b3ff858f",
    "careers-lmsc": "https://images.unsplash.com/photo-1515378791036-0648a3ef77b2",
    glossary: "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f",
};

const setImage = (type) => {
    const previewSelectors = [
        "#previewBox img",
        "#previewBoxTeaching img",
        "#previewBoxCollege img",
        "#previewBoxOnline img",
        "#previewBoxSupport img",
        "#previewBoxAbout img",
    ].join(", ");

    const targets = document.querySelectorAll(previewSelectors);
    const nextSrc = images[type];

    if (!nextSrc || targets.length === 0) {
        return;
    }

    targets.forEach((img) => {
        img.src = nextSrc;
    });
};

const menuAnchors = document.querySelectorAll(".dropdown-content a.group");

menuAnchors.forEach((anchor) => {
    const icon = anchor.querySelector("i");
    if (!icon) {
        return;
    }

    const toggleIconHighlight = (enabled) => {
        icon.classList.toggle("icon-hover-bg", enabled);
    };

    anchor.addEventListener("mouseenter", () => toggleIconHighlight(true));
    anchor.addEventListener("mouseleave", () => toggleIconHighlight(false));
    anchor.addEventListener("focus", () => toggleIconHighlight(true), true);
    anchor.addEventListener("blur", () => toggleIconHighlight(false), true);
});

const toggleAccordion = (button) => {
    if (!button) {
        return;
    }

    const content = button.nextElementSibling;
    const sign = button.querySelector("span:last-child");

    if (!content || !sign) {
        return;
    }

    document.querySelectorAll(".accordion-content").forEach((panel) => {
        if (panel !== content) {
            panel.classList.remove("open");
        }
    });

    document.querySelectorAll(".faq-button span:last-child").forEach((icon) => {
        if (icon !== sign) {
            icon.textContent = "+";
        }
    });

    content.classList.toggle("open");
    sign.textContent = content.classList.contains("open") ? "−" : "+";
};

const gap = 8;

document.querySelectorAll(".switch-btn").forEach((button) => {
    const text = button.querySelector(".text-part");
    const icon = button.querySelector(".icon-part");

    if (!text || !icon) {
        return;
    }

    let textAnimation;
    let iconAnimation;

    const stopAnimations = () => {
        if (textAnimation) {
            textAnimation.cancel();
        }
        if (iconAnimation) {
            iconAnimation.cancel();
        }
    };

    button.addEventListener("mouseenter", () => {
        const textWidth = text.offsetWidth;
        const iconWidth = icon.offsetWidth;

        stopAnimations();
        textAnimation = animate(
            text,
            { transform: `translateX(${iconWidth + gap}px)` },
            { duration: 0.35, easing: "ease-out", fill: "forwards" }
        );
        iconAnimation = animate(
            icon,
            { transform: `translateX(-${textWidth + gap}px)` },
            { duration: 0.35, easing: "ease-out", fill: "forwards" }
        );
    });

    button.addEventListener("mouseleave", () => {
        stopAnimations();
        textAnimation = animate(
            text,
            { transform: "translateX(0px)" },
            { duration: 0.35, easing: "ease-out", fill: "forwards" }
        );
        iconAnimation = animate(
            icon,
            { transform: "translateX(0px)" },
            { duration: 0.35, easing: "ease-out", fill: "forwards" }
        );
    });
});
const scrollToTopBtn = document.getElementById("scrollToTop");

if (scrollToTopBtn) {
    window.addEventListener("scroll", () => {
        if (window.scrollY > 300) {
            scrollToTopBtn.classList.add("visible");
        } else {
            scrollToTopBtn.classList.remove("visible");
        }
    });

    scrollToTopBtn.addEventListener("click", () => {
        window.scrollTo(0, 0);
    });
}

const pointerFineQuery = window.matchMedia("(pointer: fine)");
const prefersReducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
const defaultMotionEase = "cubic-bezier(0.22, 1, 0.36, 1)";
const tiltRegistry = new WeakSet();

const motionPresets = {
    fadeIn: {
        keyframes: {
            opacity: [0, 1],
            transform: ["translateY(32px)", "translateY(0px)"],
        },
        duration: 0.7,
    },
    fadeUp: {
        keyframes: {
            opacity: [0, 1],
            transform: ["translateY(40px)", "translateY(0px)"],
        },
        duration: 0.7,
    },
    slideLeft: {
        keyframes: {
            opacity: [0, 1],
            transform: ["translateX(-48px)", "translateX(0px)"],
        },
        duration: 0.65,
    },
    slideRight: {
        keyframes: {
            opacity: [0, 1],
            transform: ["translateX(48px)", "translateX(0px)"],
        },
        duration: 0.65,
    },
    scaleIn: {
        keyframes: {
            opacity: [0, 1],
            transform: ["scale(0.9)", "scale(1)"]
        },
        duration: 0.6,
    },
};

const getMotionPreset = (element) => {
    if (element.classList.contains("slide-in-left")) {
        return motionPresets.slideLeft;
    }
    if (element.classList.contains("slide-in-right")) {
        return motionPresets.slideRight;
    }
    if (element.classList.contains("scale-in")) {
        return motionPresets.scaleIn;
    }
    if (element.classList.contains("fade-up")) {
        return motionPresets.fadeUp;
    }
    return motionPresets.fadeIn;
};

const getMotionDelay = (element) => {
    const explicitDelay = element.getAttribute("data-motion-delay");
    if (explicitDelay) {
        const parsed = Number(explicitDelay);
        if (!Number.isNaN(parsed)) {
            return parsed;
        }
    }

    const staggerClass = Array.from(element.classList).find((cls) => cls.startsWith("stagger-"));
    if (staggerClass) {
        const staggerIndex = Number(staggerClass.split("-").pop());
        if (!Number.isNaN(staggerIndex)) {
            return Math.min(staggerIndex, 6) * 0.08;
        }
    }

    if (element.classList.contains("scale-in")) {
        const parent = element.parentElement;
        if (parent) {
            const siblings = Array.from(parent.children).filter((child) => child.classList?.contains("scale-in"));
            const index = siblings.indexOf(element);
            if (index >= 0) {
                return Math.min(index, 6) * 0.07;
            }
        }
    }

    return 0;
};

const signalMotionReady = (element) => {
    element.classList.add("motion-ready");
    element.style.opacity = "";
    element.style.transform = "";
    element.dispatchEvent(new CustomEvent("motion:ready"));
};

const setupViewportMotion = () => {
    const motionSelectors = [
        ".fade-in",
        ".fade-up",
        ".slide-in-left",
        ".slide-in-right",
        ".scale-in",
    ];

    const motionTargets = document.querySelectorAll(motionSelectors.join(","));

    if (motionTargets.length === 0) {
        return;
    }

    if (prefersReducedMotionQuery.matches) {
        motionTargets.forEach(signalMotionReady);
        return;
    }

    const observer = new IntersectionObserver(
        (entries, obs) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) {
                    return;
                }

                const element = entry.target;
                obs.unobserve(element);

                if (element.dataset.motionPlayed === "true") {
                    signalMotionReady(element);
                    return;
                }

                element.dataset.motionPlayed = "true";
                const preset = getMotionPreset(element);
                const delay = getMotionDelay(element);

                const animation = animate(element, preset.keyframes, {
                    duration: preset.duration,
                    easing: preset.easing ?? defaultMotionEase,
                    delay,
                    fill: "forwards",
                });

                animation.finished
                    .catch(() => undefined)
                    .finally(() => {
                        signalMotionReady(element);
                    });
            });
        },
        { rootMargin: "0px 0px -10% 0px", threshold: 0.15 }
    );

    motionTargets.forEach((element) => {
        observer.observe(element);
    });
};

const enableTilt = (element, { maxTilt = 8, scale = 1.02 } = {}) => {
    if (!element || tiltRegistry.has(element)) {
        return;
    }

    tiltRegistry.add(element);
    element.classList.add("tilt-enabled");

    let rafId = 0;

    const clamp = (value, limit) => {
        return Math.max(Math.min(value, limit), -limit);
    };

    const resetTransform = () => {
        cancelAnimationFrame(rafId);
        rafId = requestAnimationFrame(() => {
            element.classList.remove("is-interacting");
            element.style.transform = "";
        });
    };

    const updateTransform = (event) => {
        const rect = element.getBoundingClientRect();
        if (!rect.width || !rect.height) {
            return;
        }

        const relativeX = (event.clientX - rect.left) / rect.width - 0.5;
        const relativeY = (event.clientY - rect.top) / rect.height - 0.5;
        const rotateX = clamp(-relativeY * maxTilt * 2, maxTilt);
        const rotateY = clamp(relativeX * maxTilt * 2, maxTilt);

        cancelAnimationFrame(rafId);
        rafId = requestAnimationFrame(() => {
            element.classList.add("is-interacting");
            element.style.transform = `perspective(900px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(${scale})`;
        });
    };

    element.addEventListener("pointerenter", updateTransform);
    element.addEventListener("pointermove", updateTransform);
    ["pointerleave", "pointercancel", "pointerup"].forEach((eventName) => {
        element.addEventListener(eventName, resetTransform);
    });

    resetTransform();
};

const registerTiltTarget = (element, options) => {
    if (!pointerFineQuery.matches || !element) {
        return;
    }

    const activateTilt = () => enableTilt(element, options);
    const participatesInMotion = element.matches(
        ".fade-in, .fade-up, .slide-in-left, .slide-in-right, .scale-in"
    );

    if (
        element.classList.contains("motion-ready") ||
        prefersReducedMotionQuery.matches ||
        !participatesInMotion
    ) {
        activateTilt();
    } else {
        element.addEventListener("motion:ready", activateTilt, { once: true });
    }
};

const setupTiltTargets = () => {
    if (!pointerFineQuery.matches) {
        return;
    }

    const pageSlug = document.body?.dataset?.pageSlug || "";
    if (pageSlug === "contact") {
        return;
    }

    const cardSelectors = [
        ".scale-in",
        ".pricing-card",
        ".value-card",
        "[data-tilt-card]",
        ".tilt-card",
    ];

    document.querySelectorAll(cardSelectors.join(",")).forEach((card) => {
        registerTiltTarget(card, { maxTilt: 6, scale: 1.02 });
        const imageCandidates = card.querySelectorAll("img");
        imageCandidates.forEach((image) => {
            if (
                image.dataset.tiltIgnore === "true" ||
                (!image.dataset.tiltImage &&
                    !image.classList.contains("object-cover") &&
                    !image.classList.contains("rounded") &&
                    !image.classList.contains("rounded-xl") &&
                    !image.closest("figure"))
            ) {
                return;
            }
            registerTiltTarget(image, { maxTilt: 4, scale: 1.01 });
        });
    });

    document.querySelectorAll("[data-tilt], [data-tilt-image], .tilt-image").forEach((element) => {
        registerTiltTarget(element, { maxTilt: 5, scale: 1.02 });
    });
};

setupTiltTargets();
setupViewportMotion();

window.toggleSubmenu = toggleSubmenu;
window.setImage = setImage;
window.toggleAccordion = toggleAccordion;