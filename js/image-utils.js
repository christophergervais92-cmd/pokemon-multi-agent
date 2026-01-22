// Image and Product Utilities Module
// Lazy-loaded module for image optimization and product image handling

(function() {
    'use strict';
    
    // WebP support detection
    function supportsWebP() {
        if (window.webpSupport !== undefined) return window.webpSupport;
        const canvas = document.createElement('canvas');
        canvas.width = 1;
        canvas.height = 1;
        window.webpSupport = canvas.toDataURL('image/webp').indexOf('data:image/webp') === 0;
        return window.webpSupport;
    }
    
    // Get optimized image URL with WebP conversion
    function getOptimizedImageUrl(url, size = '') {
        if (!url) return url;
        if (supportsWebP() && url.includes('pokemontcg.io')) {
            const baseUrl = url.replace(/\.(jpg|jpeg|png)/i, '.webp');
            if (size && url.includes('pokemontcg.io')) {
                return baseUrl.replace(/\/(small|large|normal)\//, `/${size}/`);
            }
            return baseUrl;
        }
        return url;
    }
    
    // Generate responsive srcset for Pokemon TCG API images
    function generateSrcSet(baseUrl) {
        if (!baseUrl || !baseUrl.includes('pokemontcg.io')) return '';
        
        const sizes = ['small', 'normal', 'large'];
        const srcset = sizes.map(size => {
            const url = baseUrl.replace(/\/(small|large|normal)\//, `/${size}/`);
            const optimized = getOptimizedImageUrl(url);
            const width = size === 'small' ? '245' : size === 'normal' ? '480' : '672';
            return `${optimized} ${width}w`;
        }).join(', ');
        
        return srcset;
    }
    
    // Progressive image loading with blur-up
    function createProgressiveImage(src, alt = '', className = '', placeholder = '') {
        const webpSrc = getOptimizedImageUrl(src, 'small');
        const fallbackSrc = src;
        const srcset = generateSrcSet(src);
        const blurDataUrl = placeholder || 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="100" height="100"%3E%3Crect fill="%23171717" width="100" height="100"/%3E%3C/svg%3E';
        
        return `
            <div class="progressive-image-wrapper" style="position: relative; overflow: hidden; background: linear-gradient(135deg, #1a1a2e 0%, #2d1b4e 100%);">
                <img src="${blurDataUrl}" 
                     alt="${alt}" 
                     class="${className} progressive-image-placeholder"
                     style="filter: blur(10px); transform: scale(1.1); width: 100%; height: 100%; object-fit: cover; opacity: 0.5;"
                     loading="lazy"
                     decoding="async">
                <img src="${webpSrc || fallbackSrc}" 
                     ${srcset ? `srcset="${srcset}" sizes="(max-width: 600px) 245px, (max-width: 1200px) 480px, 672px"` : ''}
                     alt="${alt}" 
                     class="${className} progressive-image-main"
                     style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity 0.3s ease-in-out;"
                     loading="lazy"
                     decoding="async"
                     onload="this.style.opacity='1'; this.previousElementSibling.style.opacity='0';"
                     onerror="this.onerror=null; this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22100%22 height=%22100%22%3E%3Crect fill=%22%23171717%22 width=%22100%22 height=%22100%22/%3E%3C/svg%3E'; this.style.opacity='1';">
            </div>
        `;
    }
    
    // Export to global scope
    window.ImageUtils = {
        supportsWebP,
        getOptimizedImageUrl,
        generateSrcSet,
        createProgressiveImage
    };
})();
