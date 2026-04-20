/**
 * harmonix.js
 * ===========
 * Shared utilities for the Harmonix website.
 *
 * - Portuguese label maps
 * - Tag vocabulary (loaded from pairing-rules.json or hardcoded fallback)
 * - Two-tier-aware tag picker
 * - Three-mode dish form (Mode 1: composed / Mode 2: unified / Mode 3: highlights)
 * - Wine autocomplete, card builder, nav helpers
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
    'dry':        'Seco',
    'off-dry':    'Meio-Seco',
    'semi-sweet': 'Meio-Doce',
    'sweet':      'Doce',
};

const PT_FINISH = {
    'short':     'Curta',
    'medium':    'Média',
    'long':      'Longa',
    'very-long': 'Muito Longa',
};

const PT_TAG = {
    // Sabor
    salty:           'Salgado',
    acidic:          'Ácido',
    sweet:           'Doce',
    bitter:          'Amargo',
    umami:           'Umami',
    spicy:           'Picante',
    // Gordura
    fatty_animal:    'Gordura Animal',
    fatty_dairy:     'Gordura Láctea',
    fatty_vegetal:   'Gordura Vegetal',
    lean:            'Magro',
    // Método
    raw:             'Cru',
    fried:           'Frito',
    grilled:         'Grelhado',
    roasted:         'Assado',
    sauteed:         'Salteado',
    poached:         'Escalfado',
    braised:         'Estufado',
    steamed:         'A Vapor',
    cured:           'Curado',
    smoked:          'Fumado',
    // Proteína
    red_meat:        'Carne Vermelha',
    poultry:         'Aves',
    pork:            'Porco',
    game:            'Caça',
    fish_lean:       'Peixe Magro',
    fish_rich:       'Peixe Gordo',
    shellfish:       'Marisco',
    egg:             'Ovo',
    plant_protein:   'Proteína Vegetal',
    // Intensidade
    delicate:        'Delicado',
    rich:            'Rico',
    intense:         'Intenso',
    // Textura
    light:           'Leve',
    creamy:          'Cremoso',
    fatty:           'Gorduroso',
    // Aromáticos
    citrus:          'Cítrico',
    floral:          'Floral',
    herbaceous:      'Herbáceo',
    earthy:          'Terroso',
    warm_spiced:     'Especiarias Doces',
    mushroom:        'Cogumelos',
    marine:          'Marinho',
    nutty:           'Amendoado',
    smoky:           'Defumado',
    oxidative:       'Oxidativo',
    // Sabores e descritores
    sweet_sour:      'Agridoce',
    marinade:        'Marinada',
    fermented:       'Fermentado',
    pickled:         'Em Conserva',
    dessert:         'Sobremesa',
    nuts:            'Frutos Secos',
    caramel:         'Caramelo',
    chocolate:       'Chocolate',
    custard:         'Creme',
    honey:           'Mel',
    lingering:       'Persistente',
};

// Role labels for Mode 1 / 3 components
const PT_ROLE = {
    dominant_challenge: 'Dominante',
    primary:            'Principal',
    secondary:          'Secundário',
    accent:             'Acento',
    highlight:          'Destaque',
};

// ── Tag group labels (from pairing-rules.json keys) ───────────────────────────

const PT_GROUP_LABEL = {
    flavor_sauda:     'Sabor',
    fat_type:         'Gordura',
    cooking_method:   'Método',
    protein:          'Proteína',
    intensity:        'Intensidade',
    texture:          'Textura',
    aromatic:         'Aromáticos',
    flavor_descriptor:'Descritores',
    misc_flavor:      'Descritores',
};

// ── Hardcoded fallback tag groups ─────────────────────────────────────────────
// Used if pairing-rules.json is not yet loaded. Mirrors food_tags_reference.

const TAG_GROUPS_FALLBACK = [
    {
        tier: 1, section: 'Perfil estrutural',
        groups: [
            { label: 'Sabor',       tags: ['salty','acidic','sweet','bitter','umami','spicy'] },
            { label: 'Gordura',     tags: ['fatty_animal','fatty_dairy','fatty_vegetal','lean'] },
            { label: 'Método',      tags: ['raw','fried','grilled','roasted','sauteed','poached','braised','steamed','cured','smoked'] },
            { label: 'Proteína',    tags: ['red_meat','poultry','pork','game','fish_lean','fish_rich','shellfish','egg','plant_protein'] },
            { label: 'Intensidade', tags: ['delicate','rich','intense'] },
            { label: 'Textura',     tags: ['light','creamy','fatty'] },
        ],
    },
    {
        tier: 2, section: 'Aromáticos e sabores',
        groups: [
            { label: 'Aromáticos',  tags: ['citrus','floral','herbaceous','earthy','warm_spiced','mushroom','marine','nutty','smoky','oxidative'] },
            { label: 'Descritores', tags: ['sweet_sour','marinade','fermented','pickled','dessert','nuts','caramel','chocolate','custard','honey','lingering'] },
        ],
    },
];

// ── Build tag groups from loaded pairing-rules.json ───────────────────────────

/**
 * Builds the two-tier TAG_GROUPS structure from food_tags_reference.
 * @param {Object} rulesData — parsed pairing-rules.json
 * @returns {Array} same shape as TAG_GROUPS_FALLBACK
 */
function buildTagGroupsFromRules(rulesData) {
    const ref = (rulesData || {}).food_tags_reference || {};

    const tier1Groups   = [];
    const tier2Aromatic = [];
    const tier2Other    = [];

    for (const [key, val] of Object.entries(ref)) {
        if (key.startsWith('_')) continue;
        const tier = val._tier || 2;
        const tags = (val.tags || []).filter(t => t);
        if (!tags.length) continue;
        const label = PT_GROUP_LABEL[key] || key;

        if (tier === 1) {
            tier1Groups.push({ label, tags });
        } else if (key === 'aromatic') {
            tier2Aromatic.push(...tags);
        } else if (false) {
            // cultural group removed — no-op branch kept for structure
        } else {
            // flavor_descriptor, misc_flavor, etc.
            tier2Other.push(...tags);
        }
    }

    const sections = [
        { tier: 1, section: 'Perfil estrutural', groups: tier1Groups },
    ];

    const t2groups = [];
    if (tier2Aromatic.length) t2groups.push({ label: 'Aromáticos',  tags: [...new Set(tier2Aromatic)] });
    if (tier2Other.length)    t2groups.push({ label: 'Descritores', tags: [...new Set(tier2Other)]    });

    if (t2groups.length) sections.push({ tier: 2, section: 'Aromáticos e sabores', groups: t2groups });

    return sections;
}

// ── Tier-aware tag picker ─────────────────────────────────────────────────────

/**
 * Creates an interactive tag picker, tier-aware.
 * @param {HTMLElement} container
 * @param {Function}    onChange   — (Set<string>) => void
 * @param {Set}         [initial]
 * @param {Array}       [tagGroups] — from buildTagGroupsFromRules or TAG_GROUPS_FALLBACK
 */
function createTagPicker(container, onChange, initial = new Set(), tagGroups = TAG_GROUPS_FALLBACK) {
    let selected = new Set(initial);

    function updatePill(pill) {
        const tag = pill.dataset.tag;
        pill.className = 'tag-pill' + (selected.has(tag) ? ' selected' : '');
    }

    function render() {
        container.innerHTML = '';
        for (const section of tagGroups) {
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
                    pill.type = 'button';
                    pill.className = 'tag-pill' + (selected.has(tag) ? ' selected' : '');
                    pill.textContent = PT_TAG[tag] || tag;
                    pill.dataset.tag = tag;
                    pill.addEventListener('click', () => {
                        selected.has(tag) ? selected.delete(tag) : selected.add(tag);
                        updatePill(pill);
                        onChange(new Set(selected));
                    });
                    listEl.appendChild(pill);
                }

                gEl.appendChild(listEl);
                container.appendChild(gEl);
            }
        }
    }

    render();

    return {
        getSelected: () => new Set(selected),
        setSelected: (s) => {
            selected = new Set(s);
            container.querySelectorAll('.tag-pill').forEach(updatePill);
        },
        clear: () => {
            selected.clear();
            container.querySelectorAll('.tag-pill').forEach(p => { p.className = 'tag-pill'; });
            onChange(new Set());
        },
    };
}

// ── Selected tags chip row ────────────────────────────────────────────────────

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
        chip.innerHTML = `<span>${PT_TAG[tag] || tag}</span>`;
        const rm = document.createElement('button');
        rm.type = 'button';
        rm.textContent = '×';
        rm.setAttribute('aria-label', `Remover ${PT_TAG[tag] || tag}`);
        rm.addEventListener('click', () => onRemove(tag));
        chip.appendChild(rm);
        rowEl.appendChild(chip);
    }
}

// ── Three-mode dish form ──────────────────────────────────────────────────────

const MODE_INFO = {
    mode2: {
        label:    'Integrado',
        hint:     'Ingredientes cozinhados juntos — cataplana, estufado, sopa, risotto.',
    },
    mode1: {
        label:    'Composto',
        hint:     'Ingredientes servidos separadamente — tábua de queijos, sushi, charcutaria.',
    },
    mode3: {
        label:    'Com destaque',
        hint:     'Prato com identidade clara + componente significativo (molho, glacê, guarnição amarga).',
    },
};

const COMPONENT_ROLES = ['dominant_challenge', 'primary', 'secondary', 'accent'];

/**
 * Renders a full three-mode dish profiling form.
 *
 * @param {HTMLElement} container   — where to render
 * @param {Function}    onChange    — called with the current dish object on any change
 * @param {Array}       [tagGroups] — from buildTagGroupsFromRules; defaults to fallback
 *
 * @returns {{ getDish, reset }}
 *   getDish() → dish object ready for resolveDishProfile + scoreWine
 *   reset()   → clears all state and re-renders
 */
function createDishForm(container, onChange, tagGroups = TAG_GROUPS_FALLBACK) {
    let mode = 'mode2';

    // Mode 2 / Mode 3 base tags
    let baseTags = new Set();

    // Mode 1 components / Mode 3 highlights
    // Each: { id, name, role, tags: Set, generates_hard_filter }
    let components = [];

    let basePicker = null;

    // ── Emit current dish object ────────────────────────────────────────────

    function emit() {
        onChange(buildDishObj());
    }

    function buildDishObj() {
        if (mode === 'mode2') {
            const tags = [...baseTags];
            return {
                food_tags:   tags,
                primary_tag: tags[0] || null,
            };
        }

        if (mode === 'mode1') {
            return {
                components: components.map(c => ({
                    name:                 c.name,
                    role:                 c.role,
                    food_tags:            [...c.tags],
                    generates_hard_filter: c.generates_hard_filter,
                })),
            };
        }

        // mode3
        const tags = [...baseTags];
        return {
            food_tags:  tags,
            primary_tag: tags[0] || null,
            components: components.map(c => ({
                name:                 c.name,
                role:                 'highlight',
                food_tags:            [...c.tags],
                generates_hard_filter: c.generates_hard_filter,
            })),
        };
    }

    // ── Render ──────────────────────────────────────────────────────────────

    function render() {
        container.innerHTML = '';
        renderModeSelector();
        renderFormBody();
    }

    function renderModeSelector() {
        const wrap = document.createElement('div');

        const sel = document.createElement('div');
        sel.className = 'mode-selector';

        for (const [key, info] of Object.entries(MODE_INFO)) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'mode-btn' + (mode === key ? ' active' : '');
            btn.textContent = info.label;
            btn.addEventListener('click', () => {
                mode = key;
                // Reset state on mode switch
                baseTags.clear();
                components = [];
                render();
                emit();
            });
            sel.appendChild(btn);
        }

        wrap.appendChild(sel);

        const hint = document.createElement('p');
        hint.className = 'mode-hint';
        hint.textContent = MODE_INFO[mode].hint;
        wrap.appendChild(hint);

        container.appendChild(wrap);
    }

    function renderFormBody() {
        if (mode === 'mode2') renderMode2();
        else if (mode === 'mode1') renderMode1();
        else renderMode3();
    }

    // ── Mode 2: flat tags ───────────────────────────────────────────────────

    function renderMode2() {
        const wrap = document.createElement('div');
        basePicker = createTagPicker(wrap, (tags) => {
            baseTags = tags;
            emit();
        }, baseTags, tagGroups);
        container.appendChild(wrap);
    }

    // ── Mode 1: components with roles ───────────────────────────────────────

    function renderMode1() {
        const wrap = document.createElement('div');

        // Component list
        const listEl = document.createElement('div');
        listEl.className = 'component-list';
        listEl.id = 'comp-list';
        rebuildComponentList(listEl);
        wrap.appendChild(listEl);

        // Add component button
        const addBtn = document.createElement('button');
        addBtn.type = 'button';
        addBtn.className = 'btn btn-secondary btn-sm';
        addBtn.textContent = '+ Adicionar componente';
        addBtn.style.marginBottom = '6px';

        const formWrap = document.createElement('div');
        formWrap.id = 'comp-form-wrap';

        addBtn.addEventListener('click', () => {
            addBtn.style.display = 'none';
            renderAddComponentForm(formWrap, () => {
                addBtn.style.display = '';
                formWrap.innerHTML = '';
                rebuildComponentList(listEl);
                emit();
            }, () => {
                addBtn.style.display = '';
                formWrap.innerHTML = '';
            });
        });

        wrap.appendChild(addBtn);
        wrap.appendChild(formWrap);
        container.appendChild(wrap);
    }

    function rebuildComponentList(listEl) {
        listEl.innerHTML = '';
        if (!components.length) {
            const hint = document.createElement('p');
            hint.className = 'tags-empty-hint';
            hint.style.marginBottom = '10px';
            hint.textContent = 'Nenhum componente adicionado';
            listEl.appendChild(hint);
            return;
        }
        for (const comp of components) {
            listEl.appendChild(buildComponentChip(comp, () => {
                components = components.filter(c => c.id !== comp.id);
                rebuildComponentList(listEl);
                emit();
            }));
        }
    }

    function buildComponentChip(comp, onRemove) {
        const card = document.createElement('div');
        card.className = 'component-card';

        const hdr = document.createElement('div');
        hdr.className = 'component-card-header';

        const roleBadge = document.createElement('span');
        roleBadge.className = 'component-role-badge' + (comp.role === 'dominant_challenge' ? ' dominant' : '');
        roleBadge.textContent = PT_ROLE[comp.role] || comp.role;
        hdr.appendChild(roleBadge);

        const nameEl = document.createElement('span');
        nameEl.className = 'component-card-name';
        nameEl.textContent = comp.name || '—';
        hdr.appendChild(nameEl);

        const tagsEl = document.createElement('span');
        tagsEl.className = 'component-card-tags';
        tagsEl.textContent = [...comp.tags].map(t => PT_TAG[t] || t).join(', ');
        hdr.appendChild(tagsEl);

        const rmBtn = document.createElement('button');
        rmBtn.type = 'button';
        rmBtn.className = 'component-remove';
        rmBtn.textContent = '×';
        rmBtn.addEventListener('click', (e) => { e.stopPropagation(); onRemove(); });
        hdr.appendChild(rmBtn);

        card.appendChild(hdr);
        return card;
    }

    function renderAddComponentForm(wrap, onConfirm, onCancel) {
        wrap.innerHTML = '';
        const form = document.createElement('div');
        form.className = 'add-component-form';

        // Name + Role row
        const topRow = document.createElement('div');
        topRow.className = 'form-row';

        const nameGroup = document.createElement('div');
        nameGroup.className = 'form-group';
        nameGroup.style.flex = '1';
        nameGroup.innerHTML = `<label class="label">Nome</label>`;
        const nameInput = document.createElement('input');
        nameInput.className = 'form-input';
        nameInput.placeholder = 'ex: molho de laranja, dashi';
        nameGroup.appendChild(nameInput);
        topRow.appendChild(nameGroup);

        const roleGroup = document.createElement('div');
        roleGroup.className = 'form-group';
        roleGroup.innerHTML = `<label class="label">Papel</label>`;
        const roleSelect = document.createElement('select');
        roleSelect.className = 'form-select';
        for (const r of COMPONENT_ROLES) {
            const opt = document.createElement('option');
            opt.value = r;
            opt.textContent = PT_ROLE[r];
            roleSelect.appendChild(opt);
        }
        roleGroup.appendChild(roleSelect);
        topRow.appendChild(roleGroup);

        form.appendChild(topRow);

        // generates_hard_filter checkbox (shown conditionally)
        const hfRow = document.createElement('div');
        hfRow.style.marginBottom = '10px';
        const hfLabel = document.createElement('label');
        hfLabel.style.cssText = 'display:flex;align-items:center;gap:8px;font-size:12px;cursor:pointer;color:var(--muted)';
        const hfCheck = document.createElement('input');
        hfCheck.type = 'checkbox';
        hfCheck.style.accentColor = 'var(--accent)';
        hfLabel.appendChild(hfCheck);
        hfLabel.appendChild(document.createTextNode('Impõe restrições ao vinho (hard filter)'));
        hfRow.appendChild(hfLabel);

        function updateHfVisibility() {
            hfRow.style.display = roleSelect.value === 'dominant_challenge' ? '' : 'none';
        }
        roleSelect.addEventListener('change', updateHfVisibility);
        updateHfVisibility();
        form.appendChild(hfRow);

        // Tags toggle
        const tagsToggle = document.createElement('button');
        tagsToggle.type = 'button';
        tagsToggle.className = 'comp-tags-toggle';
        tagsToggle.textContent = '▶ Selecionar tags';
        form.appendChild(tagsToggle);

        const tagsBox = document.createElement('div');
        tagsBox.className = 'comp-tags-picker';
        form.appendChild(tagsBox);

        let compTags = new Set();
        let compPicker = null;

        tagsToggle.addEventListener('click', () => {
            const isOpen = tagsBox.classList.toggle('open');
            tagsToggle.textContent = (isOpen ? '▼' : '▶') + ' Selecionar tags';
            if (isOpen && !compPicker) {
                compPicker = createTagPicker(tagsBox, (tags) => {
                    compTags = tags;
                    tagsToggle.textContent = `▼ Tags (${tags.size} selecionados)`;
                }, new Set(), tagGroups);
            }
        });

        // Confirm / Cancel
        const btnRow = document.createElement('div');
        btnRow.style.cssText = 'display:flex;gap:8px;margin-top:8px';

        const confirmBtn = document.createElement('button');
        confirmBtn.type = 'button';
        confirmBtn.className = 'btn btn-primary btn-sm';
        confirmBtn.textContent = 'Adicionar';
        confirmBtn.addEventListener('click', () => {
            const name = nameInput.value.trim() || 'Componente';
            components.push({
                id:                   `comp_${Date.now()}`,
                name,
                role:                 roleSelect.value,
                tags:                 new Set(compTags),
                generates_hard_filter: hfCheck.checked,
            });
            onConfirm();
        });

        const cancelBtn = document.createElement('button');
        cancelBtn.type = 'button';
        cancelBtn.className = 'btn btn-ghost btn-sm';
        cancelBtn.textContent = 'Cancelar';
        cancelBtn.addEventListener('click', onCancel);

        btnRow.appendChild(confirmBtn);
        btnRow.appendChild(cancelBtn);
        form.appendChild(btnRow);

        wrap.appendChild(form);
    }

    // ── Mode 3: base tags + highlight components ─────────────────────────────

    function renderMode3() {
        const wrap = document.createElement('div');

        // Base tag picker
        const baseLabel = document.createElement('p');
        baseLabel.className = 'label';
        baseLabel.style.marginBottom = '12px';
        baseLabel.textContent = 'Perfil base do prato';
        wrap.appendChild(baseLabel);

        const pickerWrap = document.createElement('div');
        basePicker = createTagPicker(pickerWrap, (tags) => {
            baseTags = tags;
            emit();
        }, baseTags, tagGroups);
        wrap.appendChild(pickerWrap);

        // Divider
        const divider = document.createElement('div');
        divider.className = 'rule-line';
        wrap.appendChild(divider);

        // Highlight list
        const hlLabel = document.createElement('p');
        hlLabel.className = 'label';
        hlLabel.style.marginBottom = '12px';
        hlLabel.textContent = 'Componentes em destaque';
        wrap.appendChild(hlLabel);

        const listEl = document.createElement('div');
        listEl.className = 'component-list';
        rebuildComponentList(listEl);
        wrap.appendChild(listEl);

        // Add highlight button
        const addBtn = document.createElement('button');
        addBtn.type = 'button';
        addBtn.className = 'btn btn-secondary btn-sm';
        addBtn.textContent = '+ Adicionar destaque';

        const formWrap = document.createElement('div');

        addBtn.addEventListener('click', () => {
            addBtn.style.display = 'none';
            renderAddHighlightForm(formWrap, () => {
                addBtn.style.display = '';
                formWrap.innerHTML = '';
                rebuildComponentList(listEl);
                emit();
            }, () => {
                addBtn.style.display = '';
                formWrap.innerHTML = '';
            });
        });

        wrap.appendChild(addBtn);
        wrap.appendChild(formWrap);
        container.appendChild(wrap);
    }

    function renderAddHighlightForm(wrap, onConfirm, onCancel) {
        wrap.innerHTML = '';
        const form = document.createElement('div');
        form.className = 'add-component-form';

        const nameGroup = document.createElement('div');
        nameGroup.className = 'form-group';
        nameGroup.style.marginBottom = '10px';
        nameGroup.innerHTML = '<label class="label">Nome do destaque</label>';
        const nameInput = document.createElement('input');
        nameInput.className = 'form-input';
        nameInput.placeholder = 'ex: molho de laranja, glacê de mel';
        nameGroup.appendChild(nameInput);
        form.appendChild(nameGroup);

        const hfLabel = document.createElement('label');
        hfLabel.style.cssText = 'display:flex;align-items:center;gap:8px;font-size:12px;cursor:pointer;color:var(--muted);margin-bottom:10px';
        const hfCheck = document.createElement('input');
        hfCheck.type = 'checkbox';
        hfCheck.style.accentColor = 'var(--accent)';
        hfLabel.appendChild(hfCheck);
        hfLabel.appendChild(document.createTextNode('Impõe restrições ao vinho'));
        form.appendChild(hfLabel);

        const tagsToggle = document.createElement('button');
        tagsToggle.type = 'button';
        tagsToggle.className = 'comp-tags-toggle';
        tagsToggle.textContent = '▶ Selecionar tags';
        form.appendChild(tagsToggle);

        const tagsBox = document.createElement('div');
        tagsBox.className = 'comp-tags-picker';
        form.appendChild(tagsBox);

        let hlTags = new Set();
        let hlPicker = null;

        tagsToggle.addEventListener('click', () => {
            const isOpen = tagsBox.classList.toggle('open');
            tagsToggle.textContent = (isOpen ? '▼' : '▶') + ' Selecionar tags';
            if (isOpen && !hlPicker) {
                hlPicker = createTagPicker(tagsBox, (tags) => {
                    hlTags = tags;
                    tagsToggle.textContent = `▼ Tags (${tags.size})`;
                }, new Set(), tagGroups);
            }
        });

        const btnRow = document.createElement('div');
        btnRow.style.cssText = 'display:flex;gap:8px;margin-top:8px';

        const confirmBtn = document.createElement('button');
        confirmBtn.type = 'button';
        confirmBtn.className = 'btn btn-primary btn-sm';
        confirmBtn.textContent = 'Adicionar';
        confirmBtn.addEventListener('click', () => {
            components.push({
                id:                   `hl_${Date.now()}`,
                name:                 nameInput.value.trim() || 'Destaque',
                role:                 'highlight',
                tags:                 new Set(hlTags),
                generates_hard_filter: hfCheck.checked,
            });
            onConfirm();
        });

        const cancelBtn = document.createElement('button');
        cancelBtn.type = 'button';
        cancelBtn.className = 'btn btn-ghost btn-sm';
        cancelBtn.textContent = 'Cancelar';
        cancelBtn.addEventListener('click', onCancel);

        btnRow.appendChild(confirmBtn);
        btnRow.appendChild(cancelBtn);
        form.appendChild(btnRow);

        wrap.appendChild(form);
    }

    // ── Public API ───────────────────────────────────────────────────────────

    render();

    return {
        getDish: buildDishObj,
        reset: () => {
            mode = 'mode2';
            baseTags.clear();
            components = [];
            render();
        },
    };
}

// ── Wine card DOM builder ─────────────────────────────────────────────────────

function fmtPrice(eur) {
    return eur != null ? `€${Number(eur).toFixed(2)}` : null;
}

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

function attachWineAutocomplete(inputEl, dropdownEl, winesArray, onSelect) {
    let debounce = null;

    function showMatches(query) {
        const q = query.trim().toLowerCase();
        dropdownEl.innerHTML = '';
        if (!q || q.length < 2) { dropdownEl.classList.remove('open'); return; }

        const matches = winesArray.filter(w => {
            const hay = `${w.name} ${w.producer} ${w.region || ''} ${w.doc || ''}`.toLowerCase();
            return hay.includes(q);
        }).slice(0, 12);

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
}

// ── Tab / accordion helpers ───────────────────────────────────────────────────

function initTabs(tabsEl) {
    const btns = tabsEl.querySelectorAll('.tab-btn');
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

    if (btns[0]) btns[0].click();
}

function initAccordions(containerEl) {
    containerEl.querySelectorAll('.accordion-trigger').forEach(trigger => {
        trigger.addEventListener('click', () => {
            trigger.closest('.accordion-item').classList.toggle('open');
        });
    });
}

// ── Nav active link ───────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    const path = location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-links a').forEach(a => {
        const href = (a.getAttribute('href') || '').split('/').pop();
        if (href === path || (path === '' && href === 'index.html'))
            a.classList.add('active');
    });
});
