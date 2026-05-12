document.addEventListener('DOMContentLoaded', () => {
    const btnText = document.getElementById('btn-text');
    const downloadBtn = document.getElementById('download-btn');
    const fallbackText = document.getElementById('os-fallback');

    // ── GitHub Release Config ──
    const GITHUB_REPO = 'subhankar-patra/LocalVoice';
    const RELEASE_TAG = 'latest'; // or a specific tag like 'v1.0.0'
    const WIN_FILENAME = 'LocalVoice.exe';
    const LINUX_FILENAME = 'LocalVoice-Linux';
    const RELEASES_PAGE = `https://github.com/${GITHUB_REPO}/releases/${RELEASE_TAG}`;
    const WIN_DIRECT = `https://github.com/${GITHUB_REPO}/releases/download/${RELEASE_TAG}/${WIN_FILENAME}`;
    const LINUX_DIRECT = `https://github.com/${GITHUB_REPO}/releases/download/${RELEASE_TAG}/${LINUX_FILENAME}`;

    // Simple OS detection
    let osName = "Unknown";
    if (navigator.userAgent.indexOf("Win") != -1) osName = "Windows";
    if (navigator.userAgent.indexOf("Mac") != -1) osName = "MacOS";
    if (navigator.userAgent.indexOf("Linux") != -1) osName = "Linux";
    if (navigator.userAgent.indexOf("X11") != -1) osName = "UNIX";

    // Configure buttons based on OS
    if (osName === "Windows") {
        btnText.innerHTML = '<i class="fa-brands fa-windows" style="margin-right:8px;"></i> Download for Windows';
        downloadBtn.href = WIN_DIRECT;
        downloadBtn.setAttribute('download', '');
        
        fallbackText.innerHTML = 'Also available for <a href="' + LINUX_DIRECT + '" download><i class="fa-brands fa-linux"></i> Linux</a>';
    } 
    else if (osName === "Linux" || osName === "UNIX") {
        btnText.innerHTML = '<i class="fa-brands fa-linux" style="margin-right:8px;"></i> Download for Linux';
        downloadBtn.href = LINUX_DIRECT;
        downloadBtn.setAttribute('download', '');
        
        fallbackText.innerHTML = 'Also available for <a href="' + WIN_DIRECT + '" download><i class="fa-brands fa-windows"></i> Windows</a>';
    } 
    else if (osName === "MacOS") {
        btnText.innerHTML = '<i class="fa-brands fa-apple" style="margin-right:8px;"></i> Mac version coming soon';
        downloadBtn.style.opacity = "0.6";
        downloadBtn.style.cursor = "not-allowed";
        downloadBtn.href = "#";
        
        fallbackText.innerHTML = 'Available for <a href="' + WIN_DIRECT + '" download><i class="fa-brands fa-windows"></i> Windows</a> and <a href="' + LINUX_DIRECT + '" download><i class="fa-brands fa-linux"></i> Linux</a>';
    }
    else {
        btnText.innerHTML = '<i class="fa-solid fa-download" style="margin-right:8px;"></i> Download App';
        downloadBtn.href = RELEASES_PAGE;
        downloadBtn.target = '_blank';
    }

    // ── Download Toast Notification ──
    function createDownloadToast(fileName) {
        // Remove any existing toast
        const existing = document.querySelector('.download-toast');
        if (existing) existing.remove();

        const toast = document.createElement('div');
        toast.className = 'download-toast';
        toast.innerHTML = `
            <div class="toast-icon">
                <i class="fa-solid fa-circle-down"></i>
            </div>
            <div class="toast-body">
                <div class="toast-title">Download started!</div>
                <div class="toast-desc">${fileName} is downloading…</div>
                <div class="toast-bar"><div class="toast-bar-fill"></div></div>
            </div>
            <button class="toast-close" title="Dismiss">&times;</button>
        `;
        document.body.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => toast.classList.add('show'));

        // Close button
        toast.querySelector('.toast-close').addEventListener('click', () => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 400);
        });

        // Auto-dismiss after 8 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.classList.remove('show');
                setTimeout(() => toast.remove(), 400);
            }
        }, 8000);
    }

    // Intercept download click to show toast
    downloadBtn.addEventListener('click', (e) => {
        const href = downloadBtn.getAttribute('href');
        if (!href || href === '#') {
            e.preventDefault();
            return;
        }
        // Don't prevent default — let the browser download
        const fileName = osName === 'Windows' ? WIN_FILENAME : LINUX_FILENAME;
        createDownloadToast(fileName);
    });

    // Add smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            // Allow download links to pass through
            if (this.hasAttribute('download')) return;
            
            e.preventDefault();
            const target = document.querySelector(targetId);
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // FAQ Accordion Logic
    const faqQuestions = document.querySelectorAll('.faq-question');
    faqQuestions.forEach(question => {
        question.addEventListener('click', () => {
            const answer = question.nextElementSibling;
            
            question.classList.toggle('active');
            
            if (question.classList.contains('active')) {
                answer.style.maxHeight = answer.scrollHeight + "px";
            } else {
                answer.style.maxHeight = "0";
            }
        });
    });

    // 3D Interactive Tilt Effect for Mockup Box
    const mockup = document.querySelector('.glass-mockup');
    if (mockup) {
        mockup.addEventListener('mousemove', (e) => {
            const rect = mockup.getBoundingClientRect();
            
            // Mouse position relative to the box
            const x = e.clientX - rect.left; 
            const y = e.clientY - rect.top;  
            
            // Center of the box
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            // Calculate rotation (max 15 degrees)
            // Multiply by -1 on X so it tilts towards the mouse
            const rotateX = ((y - centerY) / centerY) * -15; 
            const rotateY = ((x - centerX) / centerX) * 15;
            
            mockup.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
        });
        
        mockup.addEventListener('mouseleave', () => {
            // Reset to default static tilt when mouse leaves
            mockup.style.transform = `perspective(1000px) rotateY(-5deg) rotateX(5deg)`;
        });
    }

    // Dynamic Copyright Year
    const yearElement = document.getElementById('current-year');
    if (yearElement) {
        yearElement.textContent = new Date().getFullYear();
    }

    // Installation OS Tabs Logic
    const tabs = document.querySelectorAll('.os-tab');
    const contents = document.querySelectorAll('.install-content');

    // Default select based on detected OS
    if (osName === "Windows") {
        document.querySelector('.os-tab[data-os="windows"]').classList.add('active');
        document.querySelector('.os-tab[data-os="linux"]').classList.remove('active');
        document.getElementById('content-windows').classList.add('active');
        document.getElementById('content-linux').classList.remove('active');
    }

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active from all tabs and contents
            tabs.forEach(t => t.classList.remove('active'));
            contents.forEach(c => c.classList.remove('active'));

            // Add active to clicked tab and corresponding content
            tab.classList.add('active');
            const targetOS = tab.getAttribute('data-os');
            document.getElementById(`content-${targetOS}`).classList.add('active');
        });
    });

    // Copy to Clipboard Logic
    const copyButtons = document.querySelectorAll('.copy-btn');
    copyButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            // Find the closest wrapper (code-block or cmd-box) and grab the inner text
            const codeWrapper = btn.closest('.code-block, .cmd-box');
            const codeBlock = codeWrapper ? codeWrapper.querySelector('code') : null;
            if (codeBlock) {
                // innerText preserves the newlines correctly
                const textToCopy = codeBlock.innerText;
                
                navigator.clipboard.writeText(textToCopy).then(() => {
                    // Store original icon
                    const originalHTML = btn.innerHTML;
                    
                    // Show checkmark
                    btn.innerHTML = '<i class="fa-solid fa-check"></i>';
                    btn.classList.add('copied');
                    
                    // Reset after 2 seconds
                    setTimeout(() => {
                        btn.innerHTML = originalHTML;
                        btn.classList.remove('copied');
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy text: ', err);
                });
            }
        });
    });

    // Intersection Observer for Latency Progress Bars Animation
    const progressBars = document.querySelectorAll('.progress-bar');
    if (progressBars.length > 0) {
        const observerOptions = {
            root: null,
            threshold: 0.1,
            rootMargin: '0px'
        };

        const barObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const bar = entry.target;
                    const width = bar.getAttribute('data-width');
                    bar.style.width = width;
                    observer.unobserve(bar); // Stop observing once animated
                }
            });
        }, observerOptions);

        progressBars.forEach(bar => barObserver.observe(bar));
    }

    // Back to Top Button Logic
    const backToTopBtn = document.getElementById('back-to-top');
    if (backToTopBtn) {
        window.addEventListener('scroll', () => {
            if (window.scrollY > window.innerHeight * 0.7) {
                backToTopBtn.classList.add('show');
            } else {
                backToTopBtn.classList.remove('show');
            }
        });

        backToTopBtn.addEventListener('click', () => {
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        });
    }

    // Fully Interactive Typing & Audio Wave Simulator
    const simStartBtn = document.getElementById('sim-start-btn');
    const simBtnLabel = document.getElementById('sim-btn-label');
    const simWave = document.getElementById('sim-wave-container');
    const simTextTarget = document.getElementById('sim-text-target');

    if (simStartBtn && simTextTarget) {
        const textToSimulate = "Writing code and typing emails with LocalVoice is incredibly fast... 🔥 Fully offline, fully private, and 18x faster than the cloud!";
        let index = 0;
        let typingInterval = null;
        let isSimulating = false;

        simStartBtn.addEventListener('click', () => {
            if (isSimulating) {
                stopSimulation();
            } else {
                startSimulation();
            }
        });

        function startSimulation() {
            isSimulating = true;
            index = 0;
            simTextTarget.textContent = "";
            simStartBtn.classList.add('active');
            simStartBtn.disabled = true; // disable until done to let animation complete
            simBtnLabel.textContent = "Listening...";
            simWave.classList.add('active');

            // Start typing letter-by-letter after a small virtual "network" delay (e.g. 300ms)
            setTimeout(() => {
                typingInterval = setInterval(() => {
                    if (index < textToSimulate.length) {
                        simTextTarget.textContent += textToSimulate.charAt(index);
                        index++;
                    } else {
                        stopSimulation();
                    }
                }, 45); // 45ms per character typing speed for incredibly snappy typing simulation
            }, 300);
        }

        function stopSimulation() {
            clearInterval(typingInterval);
            isSimulating = false;
            simStartBtn.classList.remove('active');
            simStartBtn.disabled = false;
            simBtnLabel.textContent = "Simulate Voice Input";
            simWave.classList.remove('active');
        }
    }
});
