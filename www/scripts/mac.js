// Example starter JavaScript for disabling form submissions if there are invalid fields
(() => {
    'use strict';

    const userAgent = navigator.userAgent || window.opera;

    if (/android/i.test(userAgent)) {
        var id = "android-collapse";
    } else if (/iPad|iPhone|iPod/.test(userAgent) && !window.MSStream) {
        var id = "iOS-collapse";
    } else if (/Windows/.test(userAgent)) {
        var id = "windows-collapse";
    } else if (/Macintosh/.text(userAgent)) {
        var id = "macintosh-collapse";
    } else {
        var id = "unknown";
    }

    const element = document.getElementById(id);

    if (element) {
        element.className += " show";
    }
})()

