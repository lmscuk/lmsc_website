
// Menu toggle functionality
const menuToggle = document.getElementById('menuToggle');
const closeMenu = document.getElementById('closeMenu');
const offcanvasMenu = document.getElementById('offcanvasMenu');
const offcanvasOverlay = document.getElementById('offcanvasOverlay');
const body = document.body;

function openMenu() {
    offcanvasMenu.classList.add('active');
    offcanvasOverlay.classList.add('active');
    menuToggle.classList.add('active');
    body.classList.add('menu-open');
}

function closeMenuFunc() {
    offcanvasMenu.classList.remove('active');
    offcanvasOverlay.classList.remove('active');
    menuToggle.classList.remove('active');
    body.classList.remove('menu-open');
}

menuToggle.addEventListener('click', openMenu);
closeMenu.addEventListener('click', closeMenuFunc);
offcanvasOverlay.addEventListener('click', closeMenuFunc);

// Submenu toggle functionality
function toggleSubmenu(id) {
    const submenu = document.getElementById(id + '-submenu');
    const icon = document.getElementById(id + '-icon');

    submenu.classList.toggle('active');
    icon.style.transform = submenu.classList.contains('active') ? 'rotate(180deg)' : 'rotate(0deg)';
}

// Close menu on ESC key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && offcanvasMenu.classList.contains('active')) {
        closeMenuFunc();
    }
});

// Intersection Observer for scroll animations (minified)
const observerOptions={threshold:.1,rootMargin:"0px 0px -50px 0px"},observer=new IntersectionObserver(e=>{e.forEach(t=>{t.isIntersecting&&t.target.classList.add("visible")})},observerOptions);document.addEventListener("DOMContentLoaded",()=>{document.querySelectorAll(".fade-in, .slide-in-left, .slide-in-right, .scale-in").forEach(e=>observer.observe(e));});

// Close menu on window resize to desktop
window.addEventListener('resize', () => {
    if (window.innerWidth >= 1024 && offcanvasMenu.classList.contains('active')) {
        closeMenuFunc();
    }
});


function setImage(type) {
    const images = {
        'why-lmsc': 'https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=800',
        'stem-pathways': 'https://images.unsplash.com/photo-1523580494863-6f3031224c94?w=800',
        'study-options': 'https://images.unsplash.com/photo-1554774853-b415df9eeb92?w=800',
        'fees-finance': 'https://images.unsplash.com/photo-1563013544-824ae1b704d3',
        'open-events': 'https://images.unsplash.com/photo-1523580494863-6f3031224c94?w=800',
        'prospectus': 'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=800',

        'teach-stem': 'https://images.unsplash.com/photo-1523580494863-6f3031224c94?w=800',
        'teachers': 'https://images.unsplash.com/photo-1523580494863-6f3031224c94?w=800',
        'evidence-teaching': 'https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=800',
        'learning-support': 'https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=800',
        'send-support': 'https://images.unsplash.com/photo-1526925539332-aa3b66e35444?w=800',
        'digital-learning': 'https://images.unsplash.com/photo-1587620962725-abab7fe55159?w=800',
        'facilities': 'https://images.unsplash.com/photo-1496307042754-b4aa456c4a2d?w=800',
        'research': 'https://images.unsplash.com/photo-1521791055366-0d553872125f?w=800',
        'exam-info': 'https://images.unsplash.com/photo-1496307042754-b4aa456c4a2d?w=800',

        'life-lmsc': 'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=800',
        'student-community': 'https://images.unsplash.com/photo-1496307042754-b4aa456c4a2d?w=800',
        'pastoral-care': 'https://images.unsplash.com/photo-1521747116042-5a810fda9664?w=800',
        'tutor-system': 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=800',
        'inclusion': 'https://images.unsplash.com/photo-1496307042754-b4aa456c4a2d?w=800',
        'sphere': 'https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=800',
        'faith': 'https://images.unsplash.com/photo-1521747116042-5a810fda9664?w=800',
        'assemblies': 'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=800',
        'summer-camps': 'https://images.unsplash.com/photo-1496307042754-b4aa456c4a2d?w=800',

        'online-programmes': 'https://images.unsplash.com/photo-1588196749597-9ff075ee6b5b?w=800',
        'homeschool-advice': 'https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=800',
        'computer-req': 'https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=800',
        'it-support': 'https://images.unsplash.com/photo-1587620962725-abab7fe55159?w=800',

        'faqs': "https://images.unsplash.com/photo-1522202176988-66273c2fd55f",
        'careers': "https://images.unsplash.com/photo-1503676260728-1c00da094a0b",
        'study-guidance': "https://images.unsplash.com/photo-1513258496099-48168024aec0",
        "exam-policies": "https://images.unsplash.com/photo-1509223197845-458d87318791",
        "payment-plans": "https://images.unsplash.com/photo-1563013544-824ae1b704d3",
        'blog': "https://images.unsplash.com/photo-1515378791036-0648a3ef77b2",

        'mission': "https://images.unsplash.com/photo-1454165205744-3b78555e5572",
        'vision': "https://images.unsplash.com/photo-1503676260728-1c00da094a0b",
        'principal': "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d",
        'governance': "https://images.unsplash.com/photo-1519681393784-d120267933ba",
        'partnerships': "https://images.unsplash.com/photo-1521791136064-7986c2920216",
        'history': "https://images.unsplash.com/photo-1519681393784-d120267933ba",
        'learning-space': "https://images.unsplash.com/photo-1509223197845-458d87318791",
        'alumni': "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f",
        'reports': "https://images.unsplash.com/photo-1554224155-6726b3ff858f",
        "careers-lmsc": "https://images.unsplash.com/photo-1515378791036-0648a3ef77b2",
        'glossary': "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f",
    };

    const allPreviewImgs = document.querySelectorAll(
        '#previewBox img, #previewBoxTeaching img, #previewBoxCollege img, #previewBoxOnline img, #previewBoxSupport img, #previewBoxAbout img'
    );

    allPreviewImgs.forEach(img => {
        if (!images[type]) return;

        // fade out
        img.classList.add("opacity-0");

        setTimeout(() => {
            img.src = images[type]; // change image
            img.classList.remove("opacity-0"); // fade in
        }, 300);
    });
}


const menuAnchors = document.querySelectorAll('.dropdown-content a.group');

menuAnchors.forEach(anchor => {
    const icon = anchor.querySelector('i');
    if (!icon) return;

    anchor.addEventListener('mouseenter', () => {
        icon.classList.add('icon-hover-bg');
    });

    anchor.addEventListener('mouseleave', () => {
        icon.classList.remove('icon-hover-bg');
    });

    // Optional: keyboard accessibility — change on focus/blur
    anchor.addEventListener('focus', () => {
        icon.classList.add('icon-hover-bg');
    }, true);
    anchor.addEventListener('blur', () => {
        icon.classList.remove('icon-hover-bg');
    }, true);
});

function toggleAccordion(button) {
    const content = button.nextElementSibling;
    const sign = button.querySelector('span:last-child');

    // Close all other accordion items
    document.querySelectorAll('.accordion-content').forEach(c => {
        if (c !== content) {
            c.classList.remove('open');
        }
    });

    document.querySelectorAll('.faq-button span:last-child').forEach(s => {
        if (s !== sign) {
            s.textContent = '+';
        }
    });

    // Toggle current item
    content.classList.toggle('open');
    sign.textContent = content.classList.contains('open') ? '−' : '+';
}


const gap = 8; // gap = 0.5rem

document.querySelectorAll(".switch-btn").forEach(button => {
    const text = button.querySelector(".text-part");
    const icon = button.querySelector(".icon-part");

    button.addEventListener("mouseenter", () => {
        const textWidth = text.offsetWidth;
        const iconWidth = icon.offsetWidth;

        text.style.transform = `translateX(${iconWidth + gap}px)`;
        icon.style.transform = `translateX(-${textWidth + gap}px)`;
    });

    button.addEventListener("mouseleave", () => {
        text.style.transform = `translateX(0px)`;
        icon.style.transform = `translateX(0px)`;
    });
});

// Scroll to Top Button
const scrollToTopBtn = document.getElementById('scrollToTop');

// Show/hide button based on scroll position
window.addEventListener('scroll', () => {
    if (window.pageYOffset > 300) {
        scrollToTopBtn.classList.add('visible');
    } else {
        scrollToTopBtn.classList.remove('visible');
    }
});

// Scroll to top when clicked
scrollToTopBtn.addEventListener('click', () => {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
});