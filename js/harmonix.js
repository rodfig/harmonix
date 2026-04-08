/**
 * harmonix.js
 * ===========
 * Shared utilities for the Harmonix website.
 * - Portuguese label maps
 * - Tag vocabulary (Harrington pyramid groups)
 * - Tag picker factory
 * - Wine autocomplete helper
 * - Nav active-link resolver
 *
 * No external dependencies. Loaded before page-specific scripts.
 */

// ── Portuguese label maps ─────────────────────────────────────────────────────

const PT_TYPE = {
    white:      'Branco',
    red:        'Tinto',
    rosé:       'Rosé',
    sparkling:  'Espumante',
    fortified:  'Licoroso',
};

const PT_BODY = {
    'light':        'Leve',
    'medium-light': 'Médio-Leve',
    'medium':       'Médio',
    'medium-full':  'Médio-Encorpado',
    'full':         'Encorpado',
};

const PT_SWEETNESS = {
    'dry':         'Seco',
    'off-dry':     'Meio-Seco',
    'semi-sweet':  'Meio-Doce',
    'sweet':       'Doce',
};

const PT_FINISH = {
    'short':     'Curta',
    'medium':    'Média',
    'long':      'Longa',
    'very-long': 'Muito Longa',
};

const PT_TAG = {
    // Tier 1 — flavor (SAUDA)
    salty:           'Salgado',
    acidic:          'Ácido',
    sweet:           'Doce',
    bitter:          'Amargo',
    umami:           'Umami',
    spicy:           'Picante',
    // Fat type
    fatty_animal:    'Gordura Animal',
    fatty_dairy:     'Gordura Láctea',
    fatty_vegetal:   'Gordura Vegetal',
    lean:            'Magro',
    // Method
    raw:             'Cru',
    fried:           'Frito',
    grilled:         'Grelhado',
    braised:         'Estufado',
    steamed:         'Cozido a Vapor',
    cured:           'Curado',
    smoked:          'Fumado',
    // Protein
    red_meat:        'Carne Vermelha',
    poultry:         'Aves',
    fish_lean:       'Peixe Magro',
    fish_fatty:      'Peixe Gordo',
    shellfish:       'Marisco',
    plant_protein:   'Proteína Vegetal',
    // Intensity
    delicate:        'Delicado',
    medium_intensity:'Intensidade Média',
    rich:            'Rico',
    intense:         'Intenso',
    light:           'Leve',
    // Tier 2 — aromatic
    citrus:          'Cítrico',
    floral:          'Floral',
    herbaceous:      'Herbáceo',
    earthy:          'Terroso',
    smoky:           'Fumado',
    nutty:           'Avelã/Nozes',
    resinous:        'Resinoso',
    oxidative:       'Oxidativo',
    marine:          'Marinho',
    caramel:         'Caramel',
    lemon_based:     'Limão',
    // Portuguese
    portuguese_dish: 'Prato Português',
    cataplana:       'Cataplana',
    bacalhau_based:  'Bacalhau',
    // Japanese
    dashi_based:     'Dashi',
    miso_based:      'Miso',
    yuzu:            'Yuzu',
    umami_dashi:     'Umami Dashi',
};

// ── Tag groups for the picker (Harrington pyramid) ────────────────────────────

const TAG_GROUPS = [
    {
        section: 'Base — SAUDA',
        groups: [
            { label: 'Sabores',     tags: ['salty','acidic','sweet','bitter','umami','spicy'] },
            { label: 'Intensidade', tags: ['delicate','medium_intensity','rich','intense'] },
        ],
    },
    {
        section: 'Textura — GMPC',
        groups: [
            { label: 'Gordura',   tags: ['fatty_animal','fatty_dairy','fatty_vegetal','lean'] },
            { label: 'Método',    tags: ['raw','fried','grilled','braised','steamed','cured','smoked'] },
            { label: 'Proteína',  tags: ['red_meat','poultry','fish_lean','fish_fatty','shellfish','plant_protein'] },
        ],
    },
    {
        section: 'Aromáticos & Específicos',
        groups: [
            { label: 'Aromáticos',  tags: ['citrus','floral','herbaceous','earthy','marine','nutty','smoky','resinous','oxidative'] },
            { label: 'Português',   tags: ['portuguese_dish','cataplana','bacalhau_based'] },
            { label: 'Japonês',     tags: ['dashi_based','miso_based','yuzu','umami_dashi'] },
        ],
    },
];

// ── Tag picker factory ────────────────────────────────────────────────────────

/**
 * Renders an interactive tag picker into `container`.
 * @param {HTMLElement} container
 * @param {Function}    onChange   — called with (Set<string>) on each change
 * @param {Set}         [initial]  — pre-selected tags
 * @returns {{ getSelected, setSelected, clear }}
 */
function createTagPicker(container, onChange, initial = new Set()) {
    let selected = new Set(initial);

    function render() {
        container.innerHTML = '';
        for (const section of TAG_GROUPS) {
            const secEl = document.createElement('div');
            secEl.className = 'tag-section';

            const secTitle = document.createElement('span');
            secTitle.className = 'tag-section-title';
            secTitle.textContent = section.section;
            secEl.appendChild(secTitle);

            for (const group of section.groups) {
                const gEl = document.createElement('div');
                gEl.className = 'tag-group';

                const gLabel = document.createElement('span');
                gLabel.className = 'tag-group-label';
                gLabel.textContent = group.label;
                gEl.appendChild(gLabel);

                const listEl = document.createElement('div');
                listEl.className = 'tag-list';

                for (const tag of group.tags) {
                    const pill = document.createElement('button');
                    pill.className = 'tag-pill' + (selected.has(tag) ? ' selected' : '');
                    pill.textContent = PT_TAG[tag] || tag;
                    pill.dataset.tag = tag;
                    pill.type = 'button';
                    pill.addEventListener('click', () => {
                        selected.has(tag) ? selected.delete(tag) : selected.add(tag);
                        // Re-render just this pill for performance
                        pill.className = 'tag-pill' + (selected.has(tag) ? ' selected' : '');
                        onChange(new Set(selected));
                    });
                    listEl.appendChild(pill);
                }

                gEl.appendChild(listEl);
                secEl.appendChild(gEl);
            }

            container.appendChild(secEl);
        }
    }

    render();

    return {
        getSelected: () => new Set(selected),
        setSelected: (s) => {
            selected = new Set(s);
            // Update pills without full re-render
            container.querySelectorAll('.tag-pill').forEach(pill => {
                pill.className = 'tag-pill' + (selected.has(pill.dataset.tag) ? ' selected' : '');
            });
        },
        clear: () => {
            selected.clear();
            container.querySelectorAll('.tag-pill').forEach(p => {
                p.className = 'tag-pill';
            });
            onChange(new Set());
        },
    };
}

// ── Selected tags summary row ─────────────────────────────────────────────────

/**
 * Renders selected-tag chips into `rowEl`.
 * Each chip has an ×-remove button.
 * @param {HTMLElement} rowEl
 * @param {Set}         selected
 * @param {Function}    onRemove — called with (tag) when chip is removed
 */
function renderSelectedTags(rowEl, selected, onRemove) {
    rowEl.innerHTML = '';
    if (!selected.size) {
        const hint = document.createElement('span');
        hint.className = 'tags-empty-hint';
        hint.textContent = 'Nenhum tag selecionado';
        rowEl.appendChild(hint);
        return;
    }
    for (const tag of selected) {
        const chip = document.createElement('span');
        chip.className = 'selected-tag-chip';

        const label = document.createElement('span');
        label.textContent = PT_TAG[tag] || tag;
        chip.appendChild(label);

        const rmBtn = document.createElement('button');
        rmBtn.type = 'button';
        rmBtn.textContent = '×';
        rmBtn.setAttribute('aria-label', `Remover ${PT_TAG[tag] || tag}`);
        rmBtn.addEventListener('click', () => onRemove(tag));
        chip.appendChild(rmBtn);

        rowEl.appendChild(chip);
    }
}

// ── Wine card DOM builder ─────────────────────────────────────────────────────

function fmtPrice(eur) {
    return eur != null ? `€${Number(eur).toFixed(2)}` : null;
}

/**
 * Builds and returns a .wine-card DOM element.
 * @param {Object}  w           — wine card object (from per_dish / scoreWine)
 * @param {Object}  [opts]
 * @param {boolean} [opts.hideReason]
 */
function buildWineCardEl(w, opts = {}) {
    const price  = fmtPrice(w.carta_price ?? w.price_eur);
    const type   = PT_TYPE[w.type]  || w.type  || '';
    const region = w.doc || w.region || '';
    const score  = w.score_raw != null ? w.score_raw.toFixed(1) : null;

    const card = document.createElement('div');
    card.className = 'wine-card';

    const hdr = document.createElement('div');
    hdr.className = 'wine-card-header';

    const nameEl = document.createElement('span');
    nameEl.className = 'wine-card-name';
    nameEl.textContent = w.name;
    hdr.appendChild(nameEl);

    if (score !== null) {
        const sc = document.createElement('span');
        sc.className = 'wine-card-score';
        sc.textContent = score + ' pts';
        hdr.appendChild(sc);
    }
    card.appendChild(hdr);

    const meta = document.createElement('p');
    meta.className = 'wine-card-meta';
    meta.textContent = [w.producer, type, region, price].filter(Boolean).join(' · ');
    card.appendChild(meta);

    if (w.reason && !opts.hideReason) {
        const reason = document.createElement('p');
        reason.className = 'wine-card-reason';
        reason.textContent = w.reason;
        card.appendChild(reason);
    }

    return card;
}

// ── Wine autocomplete ─────────────────────────────────────────────────────────

/**
 * Attaches a fuzzy autocomplete on `inputEl` searching `winesArray`.
 * On select, calls `onSelect(wine)`.
 * Returns { destroy }.
 */
function attachWineAutocomplete(inputEl, dropdownEl, winesArray, onSelect) {
    let debounce = null;

    function showMatches(query) {
        const q = query.trim().toLowerCase();
        dropdownEl.innerHTML = '';
        if (!q || q.length < 2) { dropdownEl.classList.remove('open'); return; }

        const matches = winesArray
            .filter(w => {
                const hay = `${w.name} ${w.producer} ${w.region || ''} ${w.doc || ''}`.toLowerCase();
                return hay.includes(q);
            })
            .slice(0, 12);

        if (!matches.length) { dropdownEl.classList.remove('open'); return; }

        for (const wine of matches) {
            const item = document.createElement('div');
            item.className = 'ac-item';

            const nameEl = document.createElement('span');
            nameEl.textContent = wine.name;
            item.appendChild(nameEl);

            const metaEl = document.createElement('span');
            metaEl.className = 'ac-item-meta';
            metaEl.textContent = [wine.producer, PT_TYPE[wine.type] || wine.type, wine.doc || wine.region].filter(Boolean).join(' · ');
            item.appendChild(metaEl);

            item.addEventListener('mousedown', (e) => {
                e.preventDefault();
                inputEl.value = '';
                dropdownEl.classList.remove('open');
                onSelect(wine);
            });

            dropdownEl.appendChild(item);
        }

        dropdownEl.classList.add('open');
    }

    inputEl.addEventListener('input', () => {
        clearTimeout(debounce);
        debounce = setTimeout(() => showMatches(inputEl.value), 180);
    });

    inputEl.addEventListener('blur', () => {
        setTimeout(() => dropdownEl.classList.remove('open'), 150);
    });

    return {
        destroy: () => {
            clearTimeout(debounce);
            inputEl.removeEventListener('input', showMatches);
        },
    };
}

// ── Tabs ──────────────────────────────────────────────────────────────────────

/**
 * Initializes tab switching for a .tabs container.
 * Buttons have data-tab="id"; panels have id matching that value.
 */
function initTabs(tabsEl) {
    const btns   = tabsEl.querySelectorAll('.tab-btn');
    const panels = [];

    btns.forEach(btn => {
        const panel = document.getElementById(btn.dataset.tab);
        if (panel) panels.push(panel);

        btn.addEventListener('click', () => {
            btns.forEach(b => b.classList.remove('active'));
            panels.forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            if (panel) panel.classList.add('active');
        });
    });

    // Activate first by default
    if (btns[0]) btns[0].click();
}

// ── Accordion ─────────────────────────────────────────────────────────────────

function initAccordions(containerEl) {
    containerEl.querySelectorAll('.accordion-trigger').forEach(trigger => {
        trigger.addEventListener('click', () => {
            const item = trigger.closest('.accordion-item');
            item.classList.toggle('open');
        });
    });
}

// ── Nav active link ───────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    const path = location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-links a').forEach(a => {
        const href = (a.getAttribute('href') || '').split('/').pop();
        if (href === path || (path === '' && href === 'index.html')) {
            a.classList.add('active');
        }
    });
});
