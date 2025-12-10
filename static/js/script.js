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
    "why-lmsc": "/static/Images/Image 8.jpg",
    "stem-pathways": "/static/Images/Image 9.jpg",
    "study-options": "/static/Images/Image 10.jpg",
    "fees-finance": "/static/Images/shutterstock_2102457391.jpg",
    "open-events": "/static/Images/Image 11.jpg",
    prospectus: "/static/Images/shutterstock_2102451193.jpg",
    "teach-stem": "/static/Images/shutterstock_2458397799.jpg",
    teachers: "/static/Images/Image 12.jpg",
    "evidence-teaching": "/static/Images/shutterstock_2478347519.jpg",
    "learning-support": "/static/Images/shutterstock_2590377907.jpg",
    "send-support": "/static/Images/shutterstock_2458397799.jpg",
    "digital-learning": "/static/Images/shutterstock_2102451193.jpg",
    facilities: "/static/Images/shutterstock_2102451331.jpg",
    research: "/static/Images/shutterstock_2478347519.jpg",
    "exam-info": "/static/Images/shutterstock_2590377907.jpg",
    "life-lmsc": "/static/Images/Image 8.jpg",
    "student-community": "/static/Images/Image 9.jpg",
    "pastoral-care": "/static/Images/Image 10.jpg",
    "tutor-system": "/static/Images/Image 11.jpg",
    inclusion: "/static/Images/Image 12.jpg",
    sphere: "/static/Images/shutterstock_2102451193.jpg",
    faith: "/static/Images/shutterstock_2458397799.jpg",
    assemblies: "/static/Images/Image 9.jpg",
    "summer-camps": "/static/Images/Image 10.jpg",
    "online-programmes": "/static/Images/Image 11.jpg",
    "homeschool-advice": "/static/Images/Image 12.jpg",
    "computer-req": "/static/Images/shutterstock_2102451193.jpg",
    "it-support": "/static/Images/shutterstock_2102457391.jpg",
    faqs: "/static/Images/shutterstock_2102451331.jpg",
    careers: "/static/Images/Image 8.jpg",
    "study-guidance": "/static/Images/Image 9.jpg",
    "exam-policies": "/static/Images/shutterstock_2590377907.jpg",
    policies: "/static/Images/shutterstock_2102451331.jpg",
    "payment-plans": "/static/Images/shutterstock_2102457391.jpg",
    blog: "/static/Images/Image 10.jpg",
    mission: "/static/Images/Image 11.jpg",
    vision: "/static/Images/Image 12.jpg",
    principal: "/static/Images/user.png",
    governance: "/static/Images/user-2.jpg",
    partnerships: "/static/Images/Image 1.jpg",
    history: "/static/Images/Image 2.jpg",
    "learning-space": "/static/Images/Image 3.jpg",
    alumni: "/static/Images/Image 4.jpg",
    reports: "/static/Images/Image 5.jpg",
    "careers-lmsc": "/static/Images/Image 6.jpg",
    glossary: "/static/Images/Image 7.jpg",
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
    const indicator = button.querySelector(".faq-indicator");

    if (!content || !indicator) {
        return;
    }

    const isOpen = content.classList.contains("open");

    document.querySelectorAll(".accordion-content").forEach((panel) => {
        if (panel === content) {
            return;
        }

        panel.classList.remove("open");
        panel.classList.add("hidden");
        panel.style.maxHeight = null;

        const panelButton = panel.previousElementSibling;
        if (panelButton) {
            panelButton.setAttribute("aria-expanded", "false");
            const panelIndicator = panelButton.querySelector(".faq-indicator");
            if (panelIndicator) {
                panelIndicator.textContent = "+";
            }
        }
    });

    if (isOpen) {
        content.classList.remove("open");
        content.classList.add("hidden");
        content.style.maxHeight = null;
        indicator.textContent = "+";
        button.setAttribute("aria-expanded", "false");
        return;
    }

    content.classList.remove("hidden");
    content.classList.add("open");
    content.style.maxHeight = `${content.scrollHeight}px`;
    indicator.textContent = "−";
    button.setAttribute("aria-expanded", "true");
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
    fadeOpacity: {
        keyframes: {
            opacity: [0, 1],
        },
        duration: 0.55,
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

const heroUnderlineAnimations = new WeakMap();

const collectHeroUnderlineTargets = (root) => {
    const selector = "[data-hero-underline]";
    if (!root) {
        return [];
    }

    if (root instanceof Element && root.matches(selector)) {
        return [root, ...root.querySelectorAll(selector)];
    }

    return Array.from(root.querySelectorAll?.(selector) ?? []);
};

const prepareHeroUnderlinePath = (path) => {
    if (!path) {
        return 1;
    }

    let pathLength = Number.parseFloat(path.dataset.heroPathLength ?? "");

    if (!Number.isFinite(pathLength) || pathLength <= 0) {
        try {
            pathLength = path.getTotalLength();
        } catch (error) {
            console.warn("Unable to measure hero underline path length", error);
            pathLength = path.getBBox?.().width || 1;
        }
        path.dataset.heroPathLength = String(pathLength);
    }

    path.style.setProperty("--path-length", pathLength);
    path.style.strokeDasharray = pathLength;

    return pathLength;
};

const playHeroUnderline = (target, { delay = 0, immediate = false } = {}) => {
    if (!target) {
        return;
    }

    const path = target.querySelector?.(".hero-underline__path");

    if (!path) {
        return;
    }

    const length = prepareHeroUnderlinePath(path);

    if (immediate || prefersReducedMotionQuery.matches) {
        path.style.strokeDashoffset = 0;
        heroUnderlineAnimations.get(path)?.cancel?.();
        heroUnderlineAnimations.delete(path);
        return;
    }

    const activeAnimation = heroUnderlineAnimations.get(path);
    if (activeAnimation) {
        activeAnimation.cancel();
        heroUnderlineAnimations.delete(path);
    }

    path.style.strokeDashoffset = length;

    const animation = animate(
        path,
        { strokeDashoffset: [length, 0] },
        {
            duration: 0.85,
            easing: defaultMotionEase,
            delay,
            fill: "forwards",
        }
    );

    heroUnderlineAnimations.set(path, animation);

    animation.finished
        .catch(() => undefined)
        .finally(() => {
            heroUnderlineAnimations.delete(path);
            path.style.strokeDashoffset = 0;
        });
};

const playHeroUnderlinesInScope = (root, options = {}) => {
    collectHeroUnderlineTargets(root).forEach((target, index) => {
        const delay = options.immediate ? 0 : index * 0.08;
        playHeroUnderline(target, { ...options, delay: (options.delay ?? 0) + delay });
    });
};

const initHeroUnderlines = () => {
    const initializeScope = (root) => {
        collectHeroUnderlineTargets(root).forEach((target) => {
            const path = target.querySelector?.(".hero-underline__path");
            if (path) {
                prepareHeroUnderlinePath(path);
            }
        });
    };

    initializeScope(document);

    if (prefersReducedMotionQuery.matches) {
        playHeroUnderlinesInScope(document, { immediate: true });
    } else {
        const activeSlide = document.querySelector(".slide.active");
        if (activeSlide) {
            playHeroUnderlinesInScope(activeSlide);
        } else {
            playHeroUnderlinesInScope(document);
        }
    }

    document.addEventListener("hero:slidechange", (event) => {
        const slide = event.detail?.slide;

        if (prefersReducedMotionQuery.matches) {
            playHeroUnderlinesInScope(slide ?? document, { immediate: true });
            return;
        }

        if (slide) {
            initializeScope(slide);
            playHeroUnderlinesInScope(slide);
            return;
        }

        playHeroUnderlinesInScope(document);
    });

    if (typeof prefersReducedMotionQuery.addEventListener === "function") {
        prefersReducedMotionQuery.addEventListener("change", (event) => {
            if (event.matches) {
                playHeroUnderlinesInScope(document, { immediate: true });
                return;
            }
            const activeSlide = document.querySelector(".slide.active");
            if (activeSlide) {
                playHeroUnderlinesInScope(activeSlide);
            } else {
                playHeroUnderlinesInScope(document);
            }
        });
    }

    window.playHeroUnderlines = (scope) => {
        if (!scope) {
            playHeroUnderlinesInScope(document, { immediate: prefersReducedMotionQuery.matches });
            return;
        }

        playHeroUnderlinesInScope(scope, { immediate: prefersReducedMotionQuery.matches });
    };
};

const getMotionPreset = (element) => {
    if (element.classList.contains("fade-opacity") || element.hasAttribute("data-tilt-card")) {
        return motionPresets.fadeOpacity;
    }
    if (element.classList.contains("slide-in-left")) {
        return motionPresets.slideLeft;
    }
    if (element.classList.contains("slide-in-right")) {
        return motionPresets.slideRight;
    }
    if (element.classList.contains("scale-in")) {
        return motionPresets.scaleIn;
    }
    if (element.classList.contains("fade-up") || element.classList.contains("fade-in-up")) {
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
    element.classList.remove("fade-in", "fade-up", "fade-in-up", "fade-opacity", "slide-in-left", "slide-in-right", "scale-in");
    element.style.opacity = "";
    element.style.transform = "";
    element.style.willChange = "";
    element.dispatchEvent(new CustomEvent("motion:ready"));
};

const setInitialMotionState = (element) => {
    if (element.dataset.motionInitialized === "true") {
        return;
    }

    element.classList.add("motion-no-transition");

    const preset = getMotionPreset(element);
    const { opacity, transform } = preset.keyframes;

    if (opacity !== undefined) {
        const initialOpacity = Array.isArray(opacity) ? opacity[0] : opacity;
        if (initialOpacity !== undefined) {
            element.style.opacity = initialOpacity;
        }
    }

    if (transform !== undefined) {
        const initialTransform = Array.isArray(transform) ? transform[0] : transform;
        if (initialTransform !== undefined) {
            element.style.transform = initialTransform;
        }
    }

    element.style.willChange = "opacity, transform";
    element.dataset.motionInitialized = "true";

    const releaseTransitions = () => {
        element.classList.remove("motion-no-transition");
    };

    if (typeof requestAnimationFrame === "function") {
        requestAnimationFrame(releaseTransitions);
    } else {
        setTimeout(releaseTransitions, 0);
    }
};

const setupViewportMotion = () => {
    const motionSelectors = [
        ".fade-in",
        ".fade-in-up",
        ".fade-up",
        ".fade-opacity",
        ".slide-in-left",
        ".slide-in-right",
        ".scale-in",
    ];

    const motionTargets = document.querySelectorAll(motionSelectors.join(","));
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initHeroUnderlines, { once: true });
} else {
    initHeroUnderlines();
}


    if (motionTargets.length === 0) {
        return;
    }

    if (prefersReducedMotionQuery.matches) {
        motionTargets.forEach((element) => {
            element.style.opacity = "";
            element.style.transform = "";
            element.style.willChange = "";
            signalMotionReady(element);
        });
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
        setInitialMotionState(element);
        observer.observe(element);
    });
};

const enableTilt = (element, { maxTilt = 6, scale = 1.02 } = {}) => {
    if (
        !element ||
        tiltRegistry.has(element) ||
        prefersReducedMotionQuery.matches ||
        !pointerFineQuery.matches
    ) {
        return;
    }

    tiltRegistry.add(element);
    element.classList.add("tilt-enabled");

    if (!/transform/.test(element.style.transition || "")) {
        const existingTransition = element.style.transition?.trim();
        element.style.transition = existingTransition
            ? `${existingTransition}, transform 0.18s ease-out`
            : "transform 0.18s ease-out";
    }

    const clamp = (value, limit) => {
        return Math.max(Math.min(value, limit), -limit);
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

        element.style.transform = `perspective(900px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(${scale})`;
    };

    const resetTransform = () => {
        element.classList.remove("is-interacting");
        element.style.transform = "";
    };

    element.addEventListener("pointerenter", (event) => {
        element.classList.add("is-interacting");
        updateTransform(event);
    });

    element.addEventListener("pointermove", updateTransform);

    ["pointerleave", "pointercancel", "pointerup"].forEach((eventName) => {
        element.addEventListener(eventName, resetTransform);
    });
};

const registerTiltTarget = (element, options) => {
    if (!element) {
        return;
    }

    enableTilt(element, options);
};

const setupTiltTargets = () => {
    const cards = document.querySelectorAll("[data-tilt-card]");
    cards.forEach((card) => {
        const maxTilt = Number.parseFloat(card.dataset.tiltMax ?? "") || 6;
        const scale = Number.parseFloat(card.dataset.tiltScale ?? "") || 1.02;
        registerTiltTarget(card, { maxTilt, scale });
    });
};

const relatedCourseSelects = document.querySelectorAll("[data-related-course-select]");

if (relatedCourseSelects.length > 0) {
    const slugInput = document.querySelector('input[name="slug"]');
    let currentSlug = slugInput ? slugInput.value.trim() : "";

    const updateSelections = () => {
        const activeValues = new Set();

        relatedCourseSelects.forEach((select) => {
            const value = select.value.trim();
            if (value) {
                activeValues.add(value);
            }
        });

        relatedCourseSelects.forEach((select) => {
            const thisValue = select.value.trim();

            Array.from(select.options).forEach((option) => {
                if (!option.value) {
                    option.disabled = false;
                    return;
                }

                const isSelf = currentSlug && option.value === currentSlug;
                const isSelectedElsewhere = option.value !== thisValue && activeValues.has(option.value);

                option.disabled = isSelf || isSelectedElsewhere;
            });
        });
    };

    relatedCourseSelects.forEach((select) => {
        select.addEventListener("change", updateSelections);
    });

    if (slugInput) {
        slugInput.addEventListener("input", () => {
            currentSlug = slugInput.value.trim();
            updateSelections();
        });
    }

    updateSelections();
}

setupViewportMotion();
setupTiltTargets();

window.toggleSubmenu = toggleSubmenu;
window.setImage = setImage;
window.toggleAccordion = toggleAccordion;