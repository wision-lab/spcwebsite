document.addEventListener('DOMContentLoaded', function () {
    const iconZoomIn = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
        <line x1="11" y1="8" x2="11" y2="14"/>
        <line x1="8" y1="11" x2="14" y2="11"/>
    </svg>`;

    const iconClose = `<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line x1="18" y1="6" x2="6" y2="18"/>
        <line x1="6" y1="6" x2="18" y2="18"/>
    </svg>`;

    // --- Shared overlay (one, reused by all sliders) ---
    const overlay = document.createElement('div');
    overlay.id = 'slider-overlay';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', 'Enlarged image comparison');
    overlay.hidden = true;

    const overlaySlider = document.createElement('img-comparison-slider');
    overlaySlider.id = 'slider-overlay-slider';
    overlaySlider.tabIndex = -1; // Make it focusable

    const closeBtn = document.createElement('button');
    closeBtn.className = 'slider-fullscreen-btn slider-overlay-close';
    closeBtn.innerHTML = iconClose;
    closeBtn.title = 'Close';
    closeBtn.setAttribute('aria-label', 'Close enlarged view');

    overlay.appendChild(overlaySlider);
    overlay.appendChild(closeBtn);
    document.body.appendChild(overlay);

    // Hide labels on overlay slider too
    overlaySlider.addEventListener('mousedown', () => overlaySlider.classList.add('labels-hidden'));
    overlaySlider.addEventListener('touchstart', () => overlaySlider.classList.add('labels-hidden'), { passive: true });
    window.addEventListener('mouseup', () => overlaySlider.classList.remove('labels-hidden'));
    window.addEventListener('touchend', () => overlaySlider.classList.remove('labels-hidden'));

    let currentSliderIndex = -1;
    let sliders = [];

    function openOverlay(slider) {
        currentSliderIndex = sliders.indexOf(slider);

        // Clone the slider's light-DOM children (the <figure> slots) into the overlay slider
        overlaySlider.innerHTML = '';
        Array.from(slider.children).forEach(function (child) {
            overlaySlider.appendChild(child.cloneNode(true));
        });

        overlaySlider.parentElement.classList.add('slider-zoomed');
        document.body.style.overflow = 'hidden';
        overlay.hidden = false;
        overlaySlider.focus();
    }

    function closeOverlay() {
        overlay.hidden = true;
        document.body.style.overflow = '';
        overlaySlider.innerHTML = '';
        overlaySlider.parentElement.classList.remove('slider-zoomed');
        currentSliderIndex = -1;
    }

    // Close on backdrop click
    overlay.addEventListener('click', function (e) {
        if (e.target === overlay) closeOverlay();
    });

    // Close on magnify button click
    closeBtn.addEventListener('click', closeOverlay);

    // Keyboard navigation
    document.addEventListener('keydown', function (e) {
        if (overlay.hidden) return;

        if (e.key === 'Escape') {
            closeOverlay();
        } else if (e.key === 'ArrowUp' && sliders.length > 0) {
            e.preventDefault();
            const nextIndex = (currentSliderIndex - 1 + sliders.length) % sliders.length;
            openOverlay(sliders[nextIndex]);
        } else if (e.key === 'ArrowDown' && sliders.length > 0) {
            e.preventDefault();
            const nextIndex = (currentSliderIndex + 1) % sliders.length;
            openOverlay(sliders[nextIndex]);
        }
    });

    // --- Per-slider setup ---
    sliders = Array.from(document.querySelectorAll('img-comparison-slider')).filter(s => s.id !== 'slider-overlay-slider');

    sliders.forEach(function (slider) {
        // Wrap slider so the magnify button can be positioned over it
        const wrapper = document.createElement('div');
        wrapper.className = 'slider-wrapper';
        slider.parentNode.insertBefore(wrapper, slider);
        wrapper.appendChild(slider);

        // Magnify button
        const btn = document.createElement('button');
        btn.className = 'slider-fullscreen-btn';
        btn.innerHTML = iconZoomIn;
        btn.title = 'Enlarge';
        btn.setAttribute('aria-label', 'Enlarge image comparison');
        wrapper.appendChild(btn);

        btn.addEventListener('click', function () { openOverlay(slider); });

        // Hide labels + button while the user drags the slider
        function hide() { wrapper.classList.add('labels-hidden'); }
        function show() { wrapper.classList.remove('labels-hidden'); }

        slider.addEventListener('mousedown', hide);
        slider.addEventListener('touchstart', hide, { passive: true });
        window.addEventListener('mouseup', show);
        window.addEventListener('touchend', show);
    });
});
