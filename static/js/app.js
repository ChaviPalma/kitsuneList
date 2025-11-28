// Netflix-style rows implementation
const galleries = [
    { id : 'mi-lista', title: 'Mi Lista', endpoint: '/api/mi-lista' },
    { id: 'recomendaciones', title: 'Nuestras Recomendaciones', endpoint: '/api/recomendaciones' },
    { id: 'joyas', title: 'Joyas de todos los tiempos', endpoint: '/api/joyas-ocultas' },
];

document.addEventListener('DOMContentLoaded', () => {
    const root = document.getElementById('rows-root');
    galleries.forEach(g => {
        const row = createRowSkeleton(g);
        root.appendChild(row);
        loadRowData(g, row.querySelector('.netflix-row'));
    });
});

function createRowSkeleton(gallery) {
    const wrapper = document.createElement('section');
    wrapper.className = 'mb-12';
    wrapper.innerHTML = `
        <div class="flex items-center justify-between mb-4">
            <h2 class="text-2xl font-bold">${gallery.title}</h2>
        </div>
        <div class="anime-scroll-container">
            <div class="netflix-row" data-endpoint="${gallery.endpoint}">
                <div class="flex items-center justify-center w-full"><div class="loading-spinner"></div></div>
            </div>
        </div>
    `;
    return wrapper;
}

async function loadRowData(gallery, rowEl) {
    try {
        // Obtener id_usuario de la URL si existe
        const urlParams = new URLSearchParams(window.location.search);
        const idUsuario = urlParams.get('id_usuario');
        
        let endpoint = gallery.endpoint;
        if (idUsuario && (gallery.endpoint.includes('recomendaciones') || gallery.endpoint.includes('joyas-ocultas') || gallery.endpoint.includes('mi-lista'))) {
            endpoint += `?id_usuario=${idUsuario}`;
        }
        
        const res = await fetch(endpoint);
        if (!res.ok) throw new Error('Fetch error');
        const data = await res.json();

        let animes = [];
        if (gallery.endpoint.includes('joyas-ocultas')) animes = data.hidden_gems || [];
        else if (gallery.endpoint.includes('recomendaciones')) animes = data.recomendaciones || [];
        else if (gallery.endpoint.includes('mi-lista')) animes = data.animes || [];

        renderRow(rowEl, animes);
    } catch (err) {
        console.error('Error loading row', gallery, err);
        rowEl.innerHTML = '<p class="text-red-400">Error al cargar</p>';
    }
}

function renderRow(rowEl, animes) {
    rowEl.innerHTML = '';
    const scrollWrap = document.createElement('div');
    scrollWrap.className = 'anime-scroll-wrapper';

    animes.forEach(anime => {
        const card = createNetflixCard(anime);
        scrollWrap.appendChild(card);
    });

    rowEl.appendChild(scrollWrap);
}

function createNetflixCard(anime) {
    const card = document.createElement('div');
    card.className = 'anime-card-horizontal';

    const title = anime.titulo_anime || anime.nombre_anime || anime.name || 'Sin título';
    const score = anime.puntuacion || anime.puntuacion_usuario || anime.rating || '';
    const episodes = anime.total_episodios || anime.episodes || '';
    const image = anime.image_url || anime.img_url || '/static/img/imagen_no_encontrada.png';
    const preview = anime.preview_url || anime.trailer_url || null;
    const animeId = anime.id_anime || '';

    card.innerHTML = `
        <div class="poster-wrap group">
            <div class="anime-poster">
                <img src="${image}" alt="${title}" loading="lazy" onerror="this.src='/static/img/imagen_no_encontrada.png'">
                ${preview ? `<video class="preview-video" muted preload="none" src="${preview}"></video>` : ''}
                <div class="overlay">
                    <div class="overlay-top flex justify-between items-center">
                        <span class="badge-rating">${score ? '⭐ '+score : ''}</span>
                    </div>
                    <div class="overlay-bottom">
                        <h4 class="line-clamp-2">${title}</h4>
                        <div class="mt-3 flex gap-2 flex-col">
                            <button class="btn-predict" data-id="${animeId}" data-title="${title}">❓ ¿Me gustará?</button>
                            <button class="btn-add" data-id="${animeId}">+ Mi lista</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Hover preview behavior
    const video = card.querySelector('.preview-video');
    if (video) {
        card.addEventListener('mouseenter', () => {
            try { video.currentTime = 0; video.play(); } catch(e){}
        });
        card.addEventListener('mouseleave', () => {
            try { video.pause(); video.currentTime = 0; } catch(e){}
        });
    }

    // Prediction behavior
    const predictBtn = card.querySelector('.btn-predict');
    predictBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        await showPrediction(animeId, title, predictBtn);
    });

    // Add to list behavior (localStorage)
    const addBtn = card.querySelector('.btn-add');
    addBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const list = JSON.parse(localStorage.getItem('mi_lista') || '[]');
        const id = addBtn.getAttribute('data-id') || title;
        if (!list.includes(id)) {
            list.push(id);
            localStorage.setItem('mi_lista', JSON.stringify(list));
            addBtn.textContent = '✓ Guardado';
            addBtn.classList.add('saved');
        }
    });

    return card;
}

async function showPrediction(animeId, title, btnElement) {
    try {
        btnElement.disabled = true;
        btnElement.textContent = '⏳ Analizando...';
        
        // Obtener id_usuario de la URL o usar por defecto
        const urlParams = new URLSearchParams(window.location.search);
        const idUsuario = urlParams.get('id_usuario') || null; // null hará que use el default del backend
        
        let url = `/api/predecir-anime/${animeId}`;
        if (idUsuario) {
            url += `?id_usuario=${idUsuario}`;
        }
        
        console.log(`Prediciendo anime ${animeId} con usuario ${idUsuario || 'default'}...`);
        
        const res = await fetch(url);
        if (!res.ok) throw new Error('Error en predicción');
        const data = await res.json();
        
        // Crear modal con resultado
        const modal = document.createElement('div');
        modal.className = 'prediction-modal';
        
        // Calcular grados del círculo (360 * probabilidad)
        const degrees = 360 * data.probabilidad;
        
        modal.innerHTML = `
            <div class="prediction-content" style="--prob: ${degrees}deg">
                <button class="close-modal">✕</button>
                <h3 class="text-2xl font-bold mb-4">${data.titulo}</h3>
                <div class="prediction-result">
                    <div class="probability-circle">
                        <span class="prob-text">${data.porcentaje}</span>
                    </div>
                    <div class="prediction-details">
                        <p class="text-lg font-semibold mb-2">
                            Predicción: <span class="prediction-value ${data.prediccion === 'Sí' ? 'yes' : 'no'}">
                                ${data.prediccion === 'Sí' ? '✓ SÍ' : '✗ NO'}
                            </span>
                        </p>
                        <p class="text-gray-300">${data.mensaje}</p>
                    </div>
                </div>
                <button class="btn-close-modal mt-6">Cerrar</button>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        modal.querySelector('.close-modal').addEventListener('click', () => modal.remove());
        modal.querySelector('.btn-close-modal').addEventListener('click', () => modal.remove());
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
        
        btnElement.disabled = false;
        btnElement.textContent = '❓ ¿Me gustará?';
        
    } catch (err) {
        console.error('Error en predicción:', err);
        btnElement.textContent = '❌ Error';
        btnElement.disabled = false;
        setTimeout(() => {
            btnElement.textContent = '❓ ¿Me gustará?';
        }, 2000);
    }
}