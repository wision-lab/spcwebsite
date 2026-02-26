document.addEventListener('DOMContentLoaded', function () {
    const iconZoomIn = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
        <line x1="11" y1="8" x2="11" y2="14"/>
        <line x1="8" y1="11" x2="14" y2="11"/>
    </svg>`;

    const iconClose = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
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
    overlaySlider.tabIndex = 0; // Make it focusable

    const closeBtn = document.createElement('button');
    closeBtn.className = 'slider-fullscreen-btn slider-overlay-close';
    closeBtn.innerHTML = iconClose;
    closeBtn.title = 'Close';
    closeBtn.setAttribute('aria-label', 'Close enlarged view');

    const overlayShortcuts = document.createElement('div');
    overlayShortcuts.className = 'overlay-shortcuts';

    overlay.appendChild(closeBtn);
    overlay.appendChild(overlaySlider);
    overlay.appendChild(overlayShortcuts);
    document.body.appendChild(overlay);

    // Hide labels on overlay slider too
    overlaySlider.addEventListener('mousedown', () => overlaySlider.classList.add('labels-hidden'));
    overlaySlider.addEventListener('touchstart', () => overlaySlider.classList.add('labels-hidden'), { passive: true });
    window.addEventListener('mouseup', () => overlaySlider.classList.remove('labels-hidden'));
    window.addEventListener('touchend', () => overlaySlider.classList.remove('labels-hidden'));

    // Hide labels when using arrow keys to move the slider in zoomed view
    overlaySlider.addEventListener('keydown', (e) => {
        if (['ArrowLeft', 'ArrowRight'].includes(e.key)) {
            overlaySlider.classList.add('labels-hidden');
        }
    });
    overlaySlider.addEventListener('keyup', (e) => {
        if (['ArrowLeft', 'ArrowRight'].includes(e.key)) {
            overlaySlider.classList.remove('labels-hidden');
        }
    });

    let currentSliderIndex = -1;
    let sliders = [];
    let isSwapped = false;
    let touchStartX = 0;
    let touchStartY = 0;
    let touchStartTime = 0;

    function applySwap(slider, swapped) {
        if (!slider || !slider.dataset.reco || !slider.dataset.gt) return;
        const img1 = slider.querySelector('img[slot="first"]');
        const img2 = slider.querySelector('img[slot="second"]');
        const cap1 = slider.querySelector('figure[slot="first"] figcaption');
        const cap2 = slider.querySelector('figure[slot="second"] figcaption');

        if (!img1 || !img2) return;

        if (swapped) {
            img1.src = slider.dataset.reco;
            img2.src = slider.dataset.gt;
            if (cap1) cap1.textContent = 'Reconstruction';
            if (cap2) cap2.textContent = 'Ground Truth';
        } else {
            img1.src = slider.dataset.gt;
            img2.src = slider.dataset.reco;
            if (cap1) cap1.textContent = 'Ground Truth';
            if (cap2) cap2.textContent = 'Reconstruction';
        }
    }

    function openOverlay(slider) {
        currentSliderIndex = sliders.indexOf(slider);

        // Clone the slider's light-DOM children (the <figure> slots) into the overlay slider
        overlaySlider.innerHTML = '';
        overlaySlider.dataset.gt = slider.dataset.gt; // Copy ground truth path

        // Copy reco path for detail view, only if it exists, otherwise swap will be enabled
        if (slider.dataset.reco) {
            overlaySlider.dataset.reco = slider.dataset.reco;
        }

        Array.from(slider.children).forEach(function (child) {
            overlaySlider.appendChild(child.cloneNode(true));
        });

        // Apply current swap state if applicable
        applySwap(overlaySlider, isSwapped);

        // Apply ground truth if keys are held
        if (heldKeys.has('1')) toggleGT(overlaySlider, 'first', true);
        if (heldKeys.has('2')) toggleGT(overlaySlider, 'second', true);

        // Set shortcuts description: show swipe hints on touch devices
        const isTouchDevice = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        if (isTouchDevice) {
            overlayShortcuts.innerHTML = '<p><b>Swipe Up / Down</b> to cycle through images. &nbsp;&bull;&nbsp; <b>Tap backdrop</b> to close.</p>';
        } else {
            const footer = document.querySelector('.shortcuts-footer');
            if (footer) {
                overlayShortcuts.innerHTML = footer.innerHTML;
            }
        }

        overlaySlider.parentElement.classList.add('slider-zoomed');
        document.body.style.overflow = 'hidden';
        overlay.hidden = false;

        // Set initial value to match source slider if possible
        if (slider.value !== undefined) {
            overlaySlider.value = slider.value;
        } else {
            overlaySlider.value = 50;
        }

        // Delay focus slightly to ensure element is visible and transition has started
        // Also use requestAnimationFrame for better browser compatibility
        requestAnimationFrame(() => {
            setTimeout(() => {
                overlaySlider.focus();
            }, 50);
        });
    }

    function closeOverlay() {
        overlay.hidden = true;
        document.body.style.overflow = '';
        overlayShortcuts.innerHTML = '';
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

    // Swipe navigation
    overlay.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
        touchStartY = e.changedTouches[0].screenY;
        touchStartTime = Date.now();
    }, { passive: true });

    overlay.addEventListener('touchend', (e) => {
        if (overlay.hidden) return;

        const touchEndX = e.changedTouches[0].screenX;
        const touchEndY = e.changedTouches[0].screenY;

        const deltaX = touchEndX - touchStartX;
        const deltaY = touchEndY - touchStartY;
        const duration = Date.now() - touchStartTime;

        const minDistance = 40; // minimum pixels
        const maxAngle = 30;    // max degrees from vertical
        const minVelocity = 0.5; // px/ms

        const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
        const velocity = distance / duration;
        const angle = Math.abs(Math.atan2(deltaX, Math.abs(deltaY))) * 180 / Math.PI;

        if (distance > minDistance && angle < maxAngle && velocity > minVelocity) {
            if (deltaY > 0) {
                // Swipe Down -> Previous
                const nextIndex = (currentSliderIndex - 1 + sliders.length) % sliders.length;
                openOverlay(sliders[nextIndex]);
            } else {
                // Swipe Up -> Next
                const nextIndex = (currentSliderIndex + 1) % sliders.length;
                openOverlay(sliders[nextIndex]);
            }
        }
    }, { passive: true });

    function toggleGT(slider, slot, isDown) {
        if (!slider) return;
        const img = slider.querySelector(`img[slot="${slot}"]`);
        const caption = slider.querySelector(`figure[slot="${slot}"] figcaption`);
        if (!img || !slider.dataset.gt || !img.dataset.original) return;

        const targetSrc = isDown ? slider.dataset.gt : img.dataset.original;
        if (img.getAttribute('src') !== targetSrc) {
            img.src = targetSrc;

            if (caption) {
                if (!caption.dataset.original) {
                    caption.dataset.original = caption.textContent;
                }
                caption.textContent = isDown ? 'Ground Truth' : caption.dataset.original;
            }
        }
    }

    const heldKeys = new Set();

    // Keyboard navigation
    document.addEventListener('keydown', function (e) {
        const key = e.key.toLowerCase();

        if (key === 's') {
            isSwapped = !isSwapped;
            sliders.forEach(s => applySwap(s, isSwapped));
            if (!overlay.hidden) applySwap(overlaySlider, isSwapped);
        }

        if (overlay.hidden) {
            if (key === 'f' && sliders.length > 0) {
                e.preventDefault();
                // Zoom in on the focused slider, or the first one if none/other is focused
                const active = document.activeElement;
                if (active && active.nodeName === 'IMG-COMPARISON-SLIDER' && active.id !== 'slider-overlay-slider') {
                    openOverlay(active);
                } else {
                    openOverlay(sliders[0]);
                }
            } else if (key === '1' || key === '2') {
                heldKeys.add(key);
                const slot = key === '1' ? 'first' : 'second';
                sliders.forEach(s => toggleGT(s, slot, true));
            }
            return;
        }

        if (e.key === 'Escape') {
            heldKeys.clear();
            closeOverlay();
        } else if (e.key === 'ArrowUp' && sliders.length > 0) {
            e.preventDefault();
            const nextIndex = (currentSliderIndex - 1 + sliders.length) % sliders.length;
            openOverlay(sliders[nextIndex]);
        } else if (e.key === 'ArrowDown' && sliders.length > 0) {
            e.preventDefault();
            const nextIndex = (currentSliderIndex + 1) % sliders.length;
            openOverlay(sliders[nextIndex]);
        } else if (key === '1' || key === '2') {
            heldKeys.add(key);
            const slot = key === '1' ? 'first' : 'second';
            toggleGT(overlaySlider, slot, true);
        }
    });

    document.addEventListener('keyup', function (e) {
        const key = e.key.toLowerCase();
        if (key === '1' || key === '2') {
            heldKeys.delete(key);
            const slot = key === '1' ? 'first' : 'second';
            if (!overlay.hidden) {
                toggleGT(overlaySlider, slot, false);
            }
            sliders.forEach(s => toggleGT(s, slot, false));
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

        // Hide labels when moving with keyboard
        slider.tabIndex = 0;
        slider.addEventListener('keydown', (e) => {
            if (['ArrowLeft', 'ArrowRight'].includes(e.key)) hide();
        });
        slider.addEventListener('keyup', (e) => {
            if (['ArrowLeft', 'ArrowRight'].includes(e.key)) show();
        });
    });
});
