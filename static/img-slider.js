document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('img-comparison-slider').forEach(function (slider) {
        function hide() { slider.classList.add('labels-hidden'); }
        function show() { slider.classList.remove('labels-hidden'); }

        slider.addEventListener('mousedown', hide);
        slider.addEventListener('touchstart', hide, { passive: true });

        window.addEventListener('mouseup', show);
        window.addEventListener('touchend', show);
    });
});

