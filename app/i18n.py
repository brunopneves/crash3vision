from __future__ import annotations

from app.version import __version__

LANG = "en"

STRINGS: dict[str, dict[str, str]] = {
    "nhtsa.error.nonpositive_ab": {
        "en": "Invalid A/B result: A (N/m) and B (N/m²) must both be greater than zero for use in Crash3Vision. Review the inputs and selected speed basis, then recalculate. This result cannot be applied or saved.",
        "pt": "Resultado A/B inválido: A (N/m) e B (N/m²) devem ser maiores que zero para uso no Crash3Vision. Revise os dados e a base de velocidade selecionada e recalcule. Este resultado não pode ser aplicado nem salvo.",
    },
    "app.title": {
        "en": f"Crash3Vision {__version__}",
        "pt": f"Crash3Vision {__version__}",
    },
    "menu.file": {
        "en": "File",
        "pt": "Arquivo",
    },
    "welcome.title": {"en": "CRASH3Vision", "pt": "CRASH3Vision"},
    "welcome.subtitle": {
        "en": "Semi-assisted analysis of vehicle deformation",
        "pt": "Análise semiassistida de deformações veiculares",
    },
    "welcome.instruction": {
        "en": "Load an image of the damaged vehicle to get started.",
        "pt": "Carregue a imagem do veículo danificado para iniciar.",
    },
    "welcome.instruction_compact": {
        "en": "Damaged vehicle image required.",
        "pt": "Imagem do veículo danificado obrigatória.",
    },
    "welcome.reference_note": {
        "en": "A reference image is optional.",
        "pt": "A imagem de referência é opcional.",
    },
    "welcome.reference_note_compact": {
        "en": "Reference optional.",
        "pt": "Referência opcional.",
    },
    "welcome.illustration": {
        "en": "Process illustration showing images, alignment and calibration, measurement, and calculation.",
        "pt": "Ilustração do processo com imagens, alinhamento e calibração, medição e cálculo.",
    },
    "welcome.step.images.title": {"en": "Images", "pt": "Imagens"},
    "welcome.step.images.description": {
        "en": "Load the vehicle photographs.",
        "pt": "Carregue as fotografias do veículo.",
    },
    "welcome.step.calibration.title": {"en": "Calibration", "pt": "Calibração"},
    "welcome.step.calibration.description": {
        "en": "Align if needed and set the scale.",
        "pt": "Alinhe se necessário e defina a escala.",
    },
    "welcome.step.measurement.title": {"en": "Measurement", "pt": "Medição"},
    "welcome.step.measurement.description": {
        "en": "Measure width W and crush C1–C6.",
        "pt": "Meça a largura W e as deformações C1–C6.",
    },
    "welcome.step.calculation.title": {"en": "Calculation", "pt": "Cálculo"},
    "welcome.step.calculation.description": {
        "en": "Calculate deformation energy and EES.",
        "pt": "Calcule a energia de deformação e a EES.",
    },
    "welcome.load_image": {"en": "Load image", "pt": "Carregar imagem"},
    "welcome.open_project": {"en": "Open project", "pt": "Abrir projeto"},
    "menu.new": {
        "en": "New project...",
        "pt": "Novo projeto...",
    },
    "menu.save_project": {
        "en": "Save project (.json)",
        "pt": "Salvar projeto (.json)",
    },
    "menu.load_project": {
        "en": "Load project (.json)",
        "pt": "Carregar projeto (.json)",
    },
    "menu.export_overlay": {
        "en": "Export annotated image...",
        "pt": "Exportar imagem anotada...",
    },
    "menu.export_current_view": {
        "en": "Export current view...",
        "pt": "Exportar visualização atual...",
    },
    "menu.export_report": {
        "en": "Export report (.txt)",
        "pt": "Exportar relatório (.txt)",
    },
    "menu.language": {
        "en": "Language",
        "pt": "Idioma",
    },
    "menu.language.english": {
        "en": "English",
        "pt": "English",
    },
    "menu.language.portuguese": {
        "en": "Português (Brasil)",
        "pt": "Português (Brasil)",
    },
    "menu.help": {"en": "Help", "pt": "Ajuda"},
    "help.close": {"en": "Close", "pt": "Fechar"},
    "help.guide.title": {"en": "How to use", "pt": "Como usar"},
    "help.methodology.title": {"en": "CRASH3 methodology", "pt": "Metodologia CRASH3"},
    "help.shortcuts.title": {"en": "Shortcuts and tools", "pt": "Atalhos e ferramentas"},
    "help.about.title": {"en": "About CRASH3Vision", "pt": "Sobre o CRASH3Vision"},
    "help.guide.body": {
        "en": """
            <ol>
              <li><b>Images.</b> The damaged vehicle image is required. A reference image is optional
              and helps compare the original and damaged contours. Then continue to Alignment.</li>
              <li><b>Alignment.</b> Orient both images with the vehicle front facing upward
              and inspect the overlay using opacity.
              Try automatic alignment, select three points on a preserved rigid region,
              or adjust manually. Review any preview before accepting it. With one image,
              or when alignment is unnecessary, continue to Calibration.</li>
              <li><b>Calibration.</b> Mark two points with a known distance in the plane of measurement,
              enter the distance in metres, and check the scale before continuing.</li>
              <li><b>Measurement.</b> With the vehicle front facing upward, mark the two ends
              of the structural damage width W. The app creates six positions. For C1–C6,
              work from left to right and mark the original structural contour, then the
              damaged contour at each position. With only the damaged vehicle image, the
              examiner establishes the original structural position using the available
              references.</li>
              <li><b>Calculation.</b> Check the source of A/B and the impact angle α.
              Calculate deformation energy. Enter the vehicle mass in kg to also estimate EES.</li>
              <li><b>Result.</b> Review EES and energy. Use the File menu to save the project
              or export an annotated image, the current view, or the text report.</li>
            </ol>
        """,
        "pt": """
            <ol>
              <li><b>Imagens.</b> Carregue a imagem do veículo danificado, que é obrigatória.
              A imagem de referência é opcional e ajuda a comparar os contornos original e
              danificado. Depois, avance para Alinhamento.</li>
              <li><b>Alinhamento.</b> Oriente as duas imagens com a dianteira voltada para cima
              e use a opacidade para conferir a sobreposição.
              Tente o alinhamento automático, marque três pontos numa região rígida preservada
              ou faça o ajuste manual. Confira a prévia quando houver, antes de aceitá-la.
              Com uma imagem ou quando o alinhamento for dispensável, avance para Calibração.</li>
              <li><b>Calibração.</b> Marque dois pontos com uma distância conhecida no plano
              da medição, informe a distância em metros e confira a escala antes de continuar.</li>
              <li><b>Medição.</b> Com a dianteira voltada para cima, marque as duas extremidades
              da largura de dano estrutural W. O aplicativo gera seis posições. Marque C1–C6
              da esquerda para a direita. Em cada posição, marque o contorno estrutural
              original e depois o contorno danificado. Com apenas a imagem do veículo
              danificado, cabe ao examinador estabelecer a posição estrutural original com
              base nas referências disponíveis.</li>
              <li><b>Cálculo.</b> Confira a origem de A/B e o ângulo de impacto α. Calcule a energia
              de deformação. Informe a massa do veículo em kg para estimar também a EES.</li>
              <li><b>Resultado.</b> Confira a EES e a energia. No menu Arquivo, salve o projeto ou
              exporte a imagem anotada, a visualização atual ou o relatório de texto.</li>
            </ol>
        """,
    },
    "help.methodology.body": {
        "en": """
            <h2>Structural measurements</h2>
            <p><b>W</b> is the width of the structural damage region selected by the examiner.
            <b>C1–C6</b> are permanent crush depths measured at six positions across that
            width, with five equal intervals of W/5. These distances are used in metres.</p>
            <h2>Coefficients and deformation energy</h2>
            <p><b>A</b> (N/m) and <b>B</b> (N/m²) describe structural stiffness. The CRASH3-derived
            formulation uses them with the damage width, the measured crush profile and an impact
            angle correction to estimate deformation energy in joules. The generic classes
            contain illustrative values. Verify the coefficient source for technical work.</p>
            {energy_equation}
            {energy_terms}
            <p align="center" style="color: #44566c; font-size: 12px;">
            (1) Estimated deformation energy E, in joules.</p>
            <h2>Energy equivalent speed (EES)</h2>
            {ees_equation}
            <p align="center" style="color: #44566c; font-size: 12px;">
            (2) Energy equivalent speed, in metres per second.</p>
            <p>E is the estimated deformation energy and m is the
            vehicle mass. EES is the speed associated with that energy and mass. It does not
            necessarily equal the actual impact speed and cannot establish it on its own.</p>
            <h2>Limitations</h2>
            <p>Calibration, perspective, image resolution and contrast, hidden structures,
            landmark selection, and coefficient suitability affect the estimate. The workflow
            is semi-assisted and was evaluated on a small sample concentrated on frontal impacts.</p>
            <p><a href="{methodology_url}">Read the project's methodology</a></p>
        """,
        "pt": """
            <h2>Medições estruturais</h2>
            <p><b>W</b> é a largura da região de dano estrutural selecionada pelo examinador.
            <b>C1–C6</b> são as profundidades de deformação permanente medidas em seis posições
            ao longo dessa largura, com cinco intervalos iguais de W/5. Essas distâncias são
            usadas em metros.</p>
            <h2>Coeficientes e energia de deformação</h2>
            <p><b>A</b> (N/m) e <b>B</b> (N/m²) descrevem a rigidez estrutural. A formulação derivada
            do CRASH3 usa esses coeficientes, a largura do dano, o perfil de deformação e uma
            correção pelo ângulo de impacto para estimar a energia de deformação em joules.
            As classes genéricas contêm valores ilustrativos. Verifique a fonte dos coeficientes
            para uso técnico.</p>
            {energy_equation}
            {energy_terms}
            <p align="center" style="color: #44566c; font-size: 12px;">
            (1) Energia de deformação estimada E, em joules.</p>
            <h2>Velocidade equivalente de energia (EES)</h2>
            {ees_equation}
            <p align="center" style="color: #44566c; font-size: 12px;">
            (2) Velocidade equivalente de energia, em metros por segundo.</p>
            <p>E é a energia de deformação estimada e m é a massa
            do veículo. A EES é a velocidade associada a essa energia e massa. Ela não corresponde
            necessariamente à velocidade real de impacto e, sozinha, não permite determiná-la.</p>
            <h2>Limitações</h2>
            <p>Calibração, perspectiva, resolução e contraste das imagens, estruturas ocultas,
            seleção de pontos e adequação dos coeficientes influenciam a estimativa.
            O procedimento é semiassistido e a validação usou uma amostra pequena, concentrada
            em impactos frontais.</p>
            <p><a href="{methodology_url}">Ler a metodologia do projeto</a></p>
        """,
    },
    "help.shortcuts.body": {
        "en": """
            <h2>Project and navigation</h2>
            <p><b>{new}</b> New project · <b>{open}</b> Open project · <b>{save}</b> Save project.</p>
            <p>Click an available step in the top bar. Use Return to current step to leave
            a previous step. On the canvas, use the mouse wheel to zoom and drag to pan
            when an editing tool is not active.</p>
            <h2>Manual alignment</h2>
            <p>With the image unlocked, the <b>arrow keys</b> move the selected image one scene pixel.
            <b>Q / E</b> decrease or increase rotation and <b>Z / X</b> decrease or increase
            scale by the configured step. Turn on Drag image to reposition it with the mouse.</p>
            <h2>Calibration and measurement</h2>
            <p>Use the on-screen controls to activate two-point marking for calibration or W.
            Select C1–C6 using the radio buttons. In C measurement mode, click near an existing
            endpoint to select it and drag vertically to adjust it. The perpendicular guide
            and crossmember offset are under Auxiliary references.</p>
        """,
        "pt": """
            <h2>Projeto e navegação</h2>
            <p><b>{new}</b> Novo projeto · <b>{open}</b> Abrir projeto · <b>{save}</b> Salvar projeto.</p>
            <p>Clique numa etapa disponível na barra superior. Use Voltar à etapa atual para
            sair de uma etapa anterior. No canvas, use a roda do mouse para zoom e arraste
            para deslocar a visualização quando não houver uma ferramenta de edição ativa.</p>
            <h2>Ajuste manual do alinhamento</h2>
            <p>Com a imagem destravada, as <b>setas</b> deslocam a imagem selecionada em um pixel na cena.
            <b>Q / E</b> diminuem ou aumentam a rotação e <b>Z / X</b> diminuem ou aumentam
            a escala pelo incremento configurado. Ative Arrastar imagem para reposicioná-la
            com o mouse.</p>
            <h2>Calibração e medição</h2>
            <p>Use os controles da etapa para ativar a marcação de dois pontos da calibração
            ou de W. Selecione C1–C6 pelos botões de seleção. No modo de medição C, clique
            perto de um ponto existente para selecioná-lo e arraste verticalmente para ajustá-lo.
            A guia perpendicular e o offset da travessa ficam em Referências auxiliares.</p>
        """,
    },
    "help.about.body": {
        "en": """
            <p><b>CRASH3Vision {version}</b></p>
            <p>Experimental research software for semi-assisted measurement of structural
            vehicle deformation from images and estimation of deformation energy and EES.</p>
            <p><b>Author</b> Bruno P. Neves<br>
            <b>License</b> <a href="{license_url}">PolyForm Noncommercial License 1.0.0</a></p>
            <p><a href="{repository_url}">GitHub · brunopneves/crash3vision</a></p>
        """,
        "pt": """
            <p><b>CRASH3Vision {version}</b></p>
            <p>Software experimental de pesquisa para medição semiassistida de deformações
            estruturais veiculares por imagens e estimativa da energia de deformação e da EES.</p>
            <p><b>Autor</b> Bruno P. Neves<br>
            <b>Licença</b> <a href="{license_url}">PolyForm Noncommercial License 1.0.0</a></p>
            <p><a href="{repository_url}">GitHub · brunopneves/crash3vision</a></p>
        """,
    },
    "dock.controls": {
        "en": "Controls",
        "pt": "Controles",
    },
    "group.images": {"en": "Images", "pt": "Imagens"},
    "images.reference": {"en": "Reference image", "pt": "Imagem de referência"},
    "images.reference_optional": {
        "en": "Reference image (optional)",
        "pt": "Imagem de referência (opcional)",
    },
    "images.deformed": {"en": "Damaged vehicle image", "pt": "Imagem do veículo danificado"},
    "images.deformed_help": {"en": "Required for measurements.", "pt": "Obrigatória para as medições."},
    "images.reference_help": {
        "en": "Used for comparison and alignment.",
        "pt": "Usada para comparação e alinhamento.",
    },
    "images.status_loaded": {"en": "✓ Loaded", "pt": "✓ Carregada"},
    "images.status_missing": {"en": "Missing", "pt": "Ausente"},
    "images.choose": {"en": "Load image", "pt": "Carregar imagem"},
    "images.replace": {"en": "Replace image", "pt": "Substituir imagem"},
    "images.choose_named": {"en": "Load {image}", "pt": "Carregar {image}"},
    "images.replace_named": {"en": "Replace {image}", "pt": "Substituir {image}"},
    "images.none_loaded": {"en": "No images loaded", "pt": "Nenhuma imagem carregada"},
    "images.both_loaded": {"en": "Both images", "pt": "Ambas as imagens"},
    "images.loaded": {"en": "Loaded images", "pt": "Imagens carregadas"},
    "images.toggle_controls": {
        "en": "Show or hide image loading and replacement controls",
        "pt": "Mostrar ou ocultar os controles de carregamento e substituição",
    },
    "label.overlay_opacity": {
        "en": "Overlay opacity",
        "pt": "Opacidade do overlay",
    },
    "group.alignment": {
        "en": "Image alignment",
        "pt": "Alinhamento das imagens",
    },
    "group.fine_adjustment": {
        "en": "Manual adjustment",
        "pt": "Ajuste manual",
    },
    "alignment.advanced": {"en": "Precision adjustments", "pt": "Ajustes de precisão"},
    "check.alignment_mode": {
        "en": "Drag image",
        "pt": "Arrastar imagem",
    },
    "check.alignment_mode_hint": {
        "en": "Alignment mode (drag selected image)",
        "pt": "Modo de alinhamento (arrastar imagem selecionada)",
    },
    "check.lock_alignment": {
        "en": "Lock alignment",
        "pt": "Travar alinhamento",
    },
    "label.editable_image": {
        "en": "Editable image:",
        "pt": "Imagem editável:",
    },
    "combo.deformed": {
        "en": "Damaged vehicle",
        "pt": "Veículo danificado",
    },
    "combo.reference": {
        "en": "Reference",
        "pt": "Referência",
    },
    "button.reset_selected_transform": {
        "en": "Reset alignment",
        "pt": "Redefinir alinhamento",
    },
    "alignment.reset.tooltip": {
        "en": "Restores the original position, rotation and scale of both images.",
        "pt": "Restaura a posição, a rotação e a escala originais das duas imagens.",
    },
    "alignment.reset.confirm": {
        "en": "Restore both images to their original positions, rotations and scales?",
        "pt": "Restaurar as posições, rotações e escalas originais das duas imagens?",
    },
    "label.alignment_method": {
        "en": "Alignment method",
        "pt": "Método de alinhamento",
    },
    "alignment.method.auto": {
        "en": "Automatic",
        "pt": "Automático",
    },
    "alignment.method.rigid": {
        "en": "By rigid region",
        "pt": "Por região rígida",
    },
    "button.start_alignment": {
        "en": "Start alignment",
        "pt": "Iniciar alinhamento",
    },
    "button.rigid_apply": {
        "en": "Apply\nalignment",
        "pt": "Aplicar\nalinhamento",
    },
    "button.rigid_try_again": {
        "en": "Try another region",
        "pt": "Tentar outra região",
    },
    "button.rigid_cancel": {
        "en": "Cancel",
        "pt": "Cancelar",
    },
    "alignment.discard_preview": {"en": "Discard\npreview", "pt": "Descartar\nprévia"},
    "alignment.rigid.instruction.reference": {
        "en": "Mark 3 points on a preserved rigid region.",
        "pt": "Marque 3 pontos sobre uma região rígida preservada.",
    },
    "alignment.rigid.instruction.suggestions": {
        "en": (
            "Suggested points are shown. Click to accept, drag to move, or "
            "click elsewhere to replace each one."
        ),
        "pt": (
            "Pontos sugeridos exibidos. Clique para aceitar, arraste para "
            "mover ou clique em outro local para substituir cada um."
        ),
    },
    "alignment.rigid.instruction.reference_progress": {
        "en": "Mark 3 points on a preserved rigid region. ({count}/3)",
        "pt": "Marque 3 pontos sobre uma região rígida preservada. ({count}/3)",
    },
    "alignment.rigid.instruction.deformed": {
        "en": "Mark approximately the same region in the damaged vehicle image.",
        "pt": "Indique aproximadamente a mesma região na imagem do veículo danificado.",
    },
    "alignment.rigid.instruction.preview": {
        "en": "Preview ready. Use it or try again.",
        "pt": "Prévia pronta. Use-a ou tente novamente.",
    },
    "alignment.rigid.title": {
        "en": "Rigid-region alignment",
        "pt": "Alinhamento por região rígida",
    },
    "alignment.rigid.second_region": {
        "en": (
            "The first search was weak or ambiguous. Indicate approximately "
            "the same region in the damaged vehicle image."
        ),
        "pt": (
            "A primeira busca foi fraca ou ambígua. Indique aproximadamente "
            "a mesma região na imagem do veículo danificado."
        ),
    },
    "alignment.rigid.failure": {
        "en": (
            "The selected regions did not produce a reliable alignment. "
            "Try other points."
        ),
        "pt": (
            "As regiões selecionadas não produziram um alinhamento confiável. "
            "Tente outros pontos."
        ),
    },
    "alignment.status.auto_medium": {
        "en": "Check the overlap of the preserved structures.",
        "pt": "Confira a sobreposição das estruturas preservadas.",
    },
    "alignment.status.auto_applied": {
        "en": "Visually check the overlap.",
        "pt": "Confira visualmente a sobreposição.",
    },
    "alignment.status.review_title": {"en": "Review alignment", "pt": "Conferir alinhamento"},
    "alignment.status.applied_title": {"en": "✓ Alignment applied", "pt": "✓ Alinhamento aplicado"},
    "alignment.status.inconclusive_title": {
        "en": "Automatic alignment inconclusive",
        "pt": "Alinhamento automático inconclusivo",
    },
    "alignment.retry_auto": {"en": "Try again", "pt": "Tentar novamente"},
    "alignment.status.single_image": {
        "en": "Continue to calibration with the loaded image.",
        "pt": "Continue para calibração com a imagem carregada.",
    },
    "alignment.undo_auto": {"en": "Undo alignment", "pt": "Desfazer alinhamento"},
    "progress.images": {"en": "Images", "pt": "Imagens"},
    "progress.alignment": {"en": "Alignment", "pt": "Alinhamento"},
    "progress.calibration": {"en": "Calibration", "pt": "Calibração"},
    "progress.measurement": {"en": "Measurement", "pt": "Medição"},
    "progress.calculation": {"en": "Calculation", "pt": "Cálculo"},
    "progress.result": {"en": "Result", "pt": "Resultado"},
    "progress.optional": {"en": "optional", "pt": "opcional"},
    "progress.skipped": {"en": "skipped", "pt": "pulado"},
    "progress.status.complete": {"en": "Complete", "pt": "Concluída"},
    "progress.status.passed": {"en": "Stage passed", "pt": "Etapa superada"},
    "progress.viewing": {"en": "Viewing · read-only", "pt": "Em consulta · somente leitura"},
    "progress.viewing_calculation": {"en": "Calculation panel open", "pt": "Painel de cálculo aberto"},
    "progress.redo": {"en": "Redo this step", "pt": "Refazer esta etapa"},
    "progress.redo.alignment": {
        "en": "Redo alignment? This resets image transforms and clears calibration, measurements, energy and EES.",
        "pt": "Refazer o alinhamento? Isso redefine as transformações das imagens e apaga a calibração, as medições, a energia e a EES.",
    },
    "progress.redo.calibration": {
        "en": "Redo calibration? This clears the scale, dependent measurements, energy and EES.",
        "pt": "Refazer a calibração? Isso apaga a escala, as medições dependentes, a energia e a EES.",
    },
    "progress.redo.measurement": {
        "en": "Redo measurement? The existing points are kept. Energy and EES are cleared.",
        "pt": "Refazer a medição? Os pontos existentes serão preservados. A energia e a EES serão apagadas.",
    },
    "progress.return_current": {"en": "Return to current step", "pt": "Voltar à etapa atual"},
    "progress.transform": {
        "en": "{image}: X {x} · Y {y} · rotation {rotation}° · scale {scale}",
        "pt": "{image}: X {x} · Y {y} · rotação {rotation}° · escala {scale}",
    },
    "progress.status.current": {"en": "Current", "pt": "Atual"},
    "progress.status.future": {"en": "Upcoming", "pt": "Futura"},
    "alignment.status.choose_method": {
        "en": "Choose an alignment method or continue directly to calibration.",
        "pt": "Escolha um método de alinhamento ou avance direto para a calibração.",
    },
    "alignment.status.auto_low": {
        "en": "Try again, choose a rigid region, adjust manually, or continue to calibration.",
        "pt": "Tente novamente, escolha uma região rígida, ajuste manualmente ou avance para a calibração.",
    },
    "button.apply_alignment_suggestion": {
        "en": "Accept\nalignment",
        "pt": "Aceitar\nalinhamento",
    },
    "alignment.auto.title": {
        "en": "Automatic alignment",
        "pt": "Alinhamento automático",
    },
    "alignment.auto.locked": {
        "en": "Unlock alignment before applying an automatic suggestion.",
        "pt": "Destrave o alinhamento antes de aplicar uma sugestão automática.",
    },
    "alignment.auto.failure": {
        "en": (
            "A reliable automatic alignment could not be obtained. "
            "Try alignment by rigid region."
        ),
        "pt": (
            "Não foi possível obter um alinhamento automático confiável. "
            "Tente o alinhamento por região rígida."
        ),
    },
    "group.nudge": {
        "en": "Translation (px)",
        "pt": "Translação (px)",
    },
    "group.rotate": {
        "en": "Rotate",
        "pt": "Rotação",
    },
    "button.rotate_minus": {
        "en": "Rotate -",
        "pt": "Rotacionar -",
    },
    "button.rotate_plus": {
        "en": "Rotate +",
        "pt": "Rotacionar +",
    },
    "label.step_deg": {
        "en": "Rotation step (°):",
        "pt": "Passo da rotação (°):",
    },
    "group.scale": {
        "en": "Scale",
        "pt": "Escala",
    },
    "button.scale_minus": {
        "en": "Scale -",
        "pt": "Escala -",
    },
    "button.scale_plus": {
        "en": "Scale +",
        "pt": "Escala +",
    },
    "label.step_pct": {
        "en": "Scale step (%):",
        "pt": "Passo da escala (%):",
    },
    "label.alignment_shortcuts": {
        "en": "Shortcuts: arrows = nudge | Q/E = rotate | Z/X = scale",
        "pt": "Atalhos: setas = ajuste fino | Q/E = rotacionar | Z/X = escala",
    },
    "button.finish_images": {"en": "Continue to alignment", "pt": "Continuar para alinhamento"},
    "button.finish_alignment": {
        "en": "Continue to calibration",
        "pt": "Continuar para calibração",
    },
    "group.calibration": {
        "en": "Calibration (px → m)",
        "pt": "Calibração (px → m)",
    },
    "check.calibration_mode": {
        "en": "Calibration mode (click 2 points)",
        "pt": "Modo de calibração (clique em 2 pontos)",
    },
    "label.measured_distance": {
        "en": "Measured distance: (px) -",
        "pt": "Distância medida: (px) -",
    },
    "label.real_distance_m": {
        "en": "Real distance (m):",
        "pt": "Distância real (m):",
    },
    "calibration.mark_points": {"en": "Mark two points", "pt": "Marcar dois pontos"},
    "calibration.remark_points": {"en": "Mark points again", "pt": "Remarcar pontos"},
    "calibration.cancel_points": {"en": "Cancel marking", "pt": "Cancelar marcação"},
    "calibration.points_title": {"en": "Calibration points", "pt": "Marcação dos pontos"},
    "calibration.points_instruction": {
        "en": "Select two points on the image with a known distance between them.",
        "pt": "Selecione dois pontos na imagem cuja distância real seja conhecida.",
    },
    "calibration.points_complete": {"en": "✓ Two points marked", "pt": "✓ Dois pontos marcados"},
    "calibration.distance_title": {"en": "Reference distance", "pt": "Distância de referência"},
    "calibration.distance_measured": {
        "en": "Measured distance: {value}",
        "pt": "Distância medida: {value}",
    },
    "calibration.distance_example": {"en": "e.g., 1.0", "pt": "Ex.: 1,0"},
    "calibration.scale_title": {"en": "Calculated scale", "pt": "Escala calculada"},
    "calibration.applied_scale_title": {"en": "Applied scale", "pt": "Escala aplicada"},
    "calibration.preview_hint": {
        "en": "The scale will be applied when you continue.",
        "pt": "A escala será aplicada ao continuar.",
    },
    "calibration.calculated_scale": {
        "en": "Calculated scale (m/px): {value}",
        "pt": "Escala calculada (m/px): {value}",
    },
    "button.apply_calibration": {
        "en": "Apply calibration",
        "pt": "Aplicar calibração",
    },
    "label.scale_m_per_px": {
        "en": "Scale: (m/px) -",
        "pt": "Escala: (m/px) -",
    },
    "button.confirm_calibration": {
        "en": "Continue to measurement",
        "pt": "Continuar para medição",
    },
    "group.marking": {
        "en": "Marking (W + C1..C6)",
        "pt": "Marcação (W + C1..C6)",
    },
    "label.marking_orientation": {
        "en": "Recommended orientation: keep the vehicle front facing upward. Mark C1–C6 from left to right.",
        "pt": "Orientação recomendada: mantenha a dianteira do veículo voltada para cima. Marque C1–C6 da esquerda para a direita.",
    },
    "marking.width": {"en": "1. Damage width (W)", "pt": "1. Largura de dano (W)"},
    "marking.crush": {"en": "2. Crush (C1–C6)", "pt": "2. Deformações (C1–C6)"},
    "marking.mark_width": {"en": "Mark W (two points)", "pt": "Marcar W (dois pontos)"},
    "marking.remark_width": {"en": "Mark W again", "pt": "Remarcar W"},
    "marking.cancel_width": {"en": "Cancel W capture", "pt": "Cancelar captura de W"},
    "marking.width_capture": {
        "en": "Click the two ends of the damage width.",
        "pt": "Clique nos dois extremos da largura de dano.",
    },
    "marking.remark_width_confirm": {
        "en": "Mark W again? Completing a new width will clear the slices, C1–C6, auxiliary references, energy and EES. Calibration will be kept.",
        "pt": "Remarcar W? Concluir uma nova largura apagará as fatias, C1–C6, as referências auxiliares, a energia e a EES. A calibração será preservada.",
    },
    "marking.slice_count": {
        "en": "{count} positions · {intervals} intervals of W/5",
        "pt": "{count} posições · {intervals} intervalos de W/5",
    },
    "marking.no_slices": {"en": "Mark W to generate C1–C6.", "pt": "Marque W para gerar C1–C6."},
    "marking.remark_for_positions": {
        "en": "Mark W again to generate C1–C6.",
        "pt": "Remarque W para gerar C1–C6.",
    },
    "marking.ci_instruction": {
        "en": "Mark with two clicks per C or drag an existing endpoint to adjust it.",
        "pt": "Marque com dois cliques por C ou arraste um ponto existente para ajustá-lo.",
    },
    "marking.ci_mark_current": {
        "en": "Mark C{idx} with two clicks, or drag an existing point.",
        "pt": "Marque C{idx} com dois cliques ou arraste um ponto existente.",
    },
    "marking.ci_complete": {"en": "C1–C6 measured.", "pt": "C1–C6 medidos."},
    "marking.ci_progress": {"en": "{count} of 6 measured", "pt": "{count} de 6 medidos"},
    "marking.references": {"en": "Auxiliary references", "pt": "Referências auxiliares"},
    "marking.guide_configured": {"en": "✓ Guide", "pt": "✓ Guia"},
    "marking.offset_configured": {"en": "✓ Offset", "pt": "✓ Offset"},
    "check.set_w_mode": {
        "en": "Set W mode (click 2 points: left/right)",
        "pt": "Modo definir W (2 cliques: esquerda/direita)",
    },
    "label.w_default": {
        "en": "W: — m",
        "pt": "W: — m",
    },
    "button.generate_slices": {
        "en": "Generate 6 slices",
        "pt": "Gerar 6 fatias",
    },
    "label.delta_w_default": {
        "en": "ΔW: — px · — m",
        "pt": "ΔW: — px · — m",
    },
    "check.set_guide_mode": {
        "en": "Perpendicular guide",
        "pt": "Guia perpendicular",
    },
    "marking.guide_hint": {
        "en": "Click the canvas to place the perpendicular guide.",
        "pt": "Clique no canvas para posicionar a guia perpendicular.",
    },
    "check.measure_ci_mode": {
        "en": "Measure or adjust C",
        "pt": "Medir ou ajustar C",
    },
    "label.current_ci": {
        "en": "Current: C{idx}",
        "pt": "Atual: C{idx}",
    },
    "group.select_c": {
        "en": "Select C to edit",
        "pt": "Selecione C para editar",
    },
    "label.c_values_default": {
        "en": "C values (m): C1=-  C2=-  C3=-  C4=-  C5=-  C6=-",
        "pt": "Valores de C (m): C1=-  C2=-  C3=-  C4=-  C5=-  C6=-",
    },
    "button.finish_marking": {
        "en": "Continue to calculation",
        "pt": "Continuar para cálculo",
    },
    "group.workflow": {
        "en": "Workflow",
        "pt": "Fluxo",
    },
    "button.restart_alignment": {
        "en": "Restart from alignment",
        "pt": "Reiniciar do alinhamento",
    },
    "button.restart_calibration": {
        "en": "Restart from calibration",
        "pt": "Reiniciar da calibração",
    },
    "button.restart_marking": {
        "en": "Restart marking",
        "pt": "Reiniciar marcação",
    },
    "result.ees_title": {
        "en": "Energy equivalent speed (EES)",
        "pt": "Velocidade equivalente de energia (EES)",
    },
    "result.ees_kmh": {"en": "{value} km/h", "pt": "{value} km/h"},
    "result.ees_mps": {"en": "{value} m/s", "pt": "{value} m/s"},
    "result.energy_title": {
        "en": "Deformation energy",
        "pt": "Energia de deformação",
    },
    "result.energy_j": {"en": "{value} J", "pt": "{value} J"},
    "result.context_title": {"en": "Calculation context", "pt": "Contexto do cálculo"},
    "dialog.export_report": {
        "en": "Export report",
        "pt": "Exportar relatório",
    },
    "dialog.saved": {
        "en": "Saved: {path}",
        "pt": "Salvo: {path}",
    },
    "warning.generate_slices_first": {
        "en": "Generate slices first.",
        "pt": "Gere os slices primeiro.",
    },
    "warning.set_w_first": {
        "en": "Set W first (2 clicks).",
        "pt": "Defina W primeiro (2 cliques).",
    },
    "report.title": {
        "en": "CRASH3Vision — Technical calculation summary",
        "pt": "CRASH3Vision — Resumo técnico de cálculo",
    },
    "report.app_version": {
        "en": "Application version",
        "pt": "Versão do aplicativo",
    },
    "report.number_notation": {
        "en": "Numbers use a decimal point with no thousands separators. A dash (-) marks unavailable data.",
        "pt": "Os números usam ponto decimal sem separadores de milhares. Um traço (-) indica dado indisponível.",
    },
    "report.images_and_calibration": {
        "en": "IMAGES AND CALIBRATION",
        "pt": "IMAGENS E CALIBRAÇÃO",
    },
    "report.calibration_distance_px": {
        "en": "Distance between calibration points (px)",
        "pt": "Distância entre os pontos de calibração (px)",
    },
    "report.calibration_distance_m": {
        "en": "Real distance reconstructed from points and saved scale (m)",
        "pt": "Distância real reconstruída dos pontos e da escala gravada (m)",
    },
    "report.calibration_point": {
        "en": "Calibration point {index} (scene px)",
        "pt": "Ponto de calibração {index} (px da cena)",
    },
    "report.calculation_parameters": {
        "en": "CALCULATION PARAMETERS",
        "pt": "PARÂMETROS DO CÁLCULO",
    },
    "report.images": {
        "en": "IMAGES",
        "pt": "IMAGENS",
    },
    "report.reference": {
        "en": "Reference",
        "pt": "Referência",
    },
    "report.deformed": {
        "en": "Deformed",
        "pt": "Deformada",
    },
    "report.calibration": {
        "en": "CALIBRATION",
        "pt": "CALIBRAÇÃO",
    },
    "report.markings": {
        "en": "MARKINGS",
        "pt": "MARCAÇÕES",
    },
    "report.crash3_params": {
        "en": "CRASH3 PARAMETERS",
        "pt": "PARÂMETROS CRASH3",
    },
    "report.results": {
        "en": "DEFORMATION ENERGY AND EES",
        "pt": "ENERGIA DE DEFORMAÇÃO E EES",
    },
    "report.project": {
        "en": "Project",
        "pt": "Projeto",
    },
    "report.datetime": {
        "en": "Generated at",
        "pt": "Data e hora de geração",
    },
    "report.scale_m_per_px": {
        "en": "Scale (m/px)",
        "pt": "Escala (m/px)",
    },
    "report.total_energy_j": {
        "en": "Total energy (J)",
        "pt": "Energia total (J)",
    },
    "report.vehicle_mass_kg": {
        "en": "Vehicle mass (kg)",
        "pt": "Massa do veículo (kg)",
    },
    "report.damage_speed_mps": {
        "en": "Damage speed of the source test (m/s)",
        "pt": "Velocidade de dano do ensaio de origem (m/s)",
    },
    "report.damage_speed_kmh": {
        "en": "Damage speed (km/h)",
        "pt": "Velocidade de dano (km/h)",
    },
    "report.damage_markings": {
        "en": "DAMAGE MARKINGS",
        "pt": "MARCAÇÕES DE DEFORMAÇÃO",
    },
    "report.crash3_params_extended": {
        "en": "CRASH3 PARAMETERS",
        "pt": "PARÂMETROS CRASH3",
    },
    "report.calculation_angle_deg": {
        "en": "Calculation angle α (°)",
        "pt": "Ângulo de cálculo α (°)",
    },
    "report.si_units_full": {
        "en": "Unit system: SI (N/m, N/m², m, s)",
        "pt": "Sistema de unidades: SI (N/m, N/m², m, s)",
    },
    "report.ab_source_full": {
        "en": "STIFFNESS COEFFICIENTS (A/B) AND SOURCE",
        "pt": "COEFICIENTES DE RIGIDEZ (A/B) E PROCEDÊNCIA",
    },
    "report.method": {
        "en": "Method",
        "pt": "Método",
    },
    "report.method.nhtsa_report": {
        "en": "Derived from crash test report (NHTSA)",
        "pt": "Derivado de ensaio de colisão (NHTSA)",
    },
    "report.method.nhtsa_library": {
        "en": "Loaded from NHTSA library",
        "pt": "Carregado da biblioteca NHTSA",
    },
    "report.method.generic_class": {
        "en": "Generic stiffness class",
        "pt": "Classe genérica de rigidez",
    },
    "report.method.manual": {
        "en": "Manual entry",
        "pt": "Entrada manual",
    },
    "report.test_description": {
        "en": "SOURCE TEST FOR A/B",
        "pt": "ENSAIO DE ORIGEM DOS COEFICIENTES A/B",
    },
    "report.generic_illustrative": {
        "en": "Generic-class coefficients are illustrative.",
        "pt": "Os coeficientes de classes genéricas são ilustrativos.",
    },
    "report.test_vehicle": {"en": "Test vehicle", "pt": "Veículo do ensaio"},
    "report.test_agency": {"en": "Test agency", "pt": "Órgão responsável pelo ensaio"},
    "report.test_width": {"en": "Test crush profile width L (m)", "pt": "Largura L do perfil de deformação do ensaio (m)"},
    "report.test_crush": {"en": "Test crush values for A/B (m)", "pt": "Deformações do ensaio usadas para A/B (m)"},
    "report.test_type": {
        "en": "Test type",
        "pt": "Tipo de teste",
    },
    "report.test_configuration": {
        "en": "Test configuration",
        "pt": "Configuração do teste",
    },
    "report.barrier_type": {
        "en": "Barrier type",
        "pt": "Tipo de barreira",
    },
    "report.impact_direction": {
        "en": "Impact direction",
        "pt": "Direção do impacto",
    },
    "report.overlap_pct": {
        "en": "Overlap (%)",
        "pt": "Sobreposição (%)",
    },
    "report.test_speed_mps": {
        "en": "Test speed (m/s)",
        "pt": "Velocidade do ensaio (m/s)",
    },
    "report.impact_angle_deg": {
        "en": "Impact angle (deg)",
        "pt": "Ângulo de impacto (deg)",
    },
    "report.test_number": {
        "en": "Test number",
        "pt": "Número do teste",
    },
    "report.report_number": {
        "en": "Report number",
        "pt": "Número do relatório",
    },
    "report.methodology": {
        "en": "METHODOLOGICAL NOTES AND LIMITATIONS",
        "pt": "OBSERVAÇÕES METODOLÓGICAS E LIMITAÇÕES",
    },
    "report.methodology.energy": {
        "en": "The CRASH3-derived formulation estimates deformation energy from W, C1–C6, stiffness coefficients A and B, and angle α.",
        "pt": "A formulação derivada do CRASH3 estima a energia de deformação a partir de W, C1–C6, dos coeficientes A e B e do ângulo α.",
    },
    "report.methodology.speed": {
        "en": (
            "Energy Equivalent Speed (EES) is the speed equivalent to the estimated deformation energy "
            "for the mass used (EES = √(2E/m)). It does not necessarily equal the actual impact speed."
        ),
        "pt": (
            "A Velocidade Equivalente de Energia (EES) é a velocidade equivalente à energia de deformação "
            "estimada para a massa utilizada (EES = √(2E/m)). Ela não corresponde necessariamente à velocidade real de impacto."
        ),
    },
    "report.methodology.scope": {
        "en": "This technical calculation summary does not, on its own, constitute a conclusive forensic report.",
        "pt": "Este resumo técnico de cálculo não constitui, isoladamente, um laudo pericial conclusivo.",
    },
    "report.total_energy_deformation_j": {
        "en": "Total deformation energy (J)",
        "pt": "Energia total de deformação (J)",
    },
    "report.vehicle_mass_considered_kg": {
        "en": "Vehicle mass considered (kg)",
        "pt": "Massa do veículo considerada (kg)",
    },
    "calc.group.title": {
        "en": "CRASH3 Calculation",
        "pt": "Cálculo CRASH3",
    },
    "calc.generic_class": {
        "en": "Generic stiffness class",
        "pt": "Classe genérica de rigidez",
    },
    "calc.manual_entry": {
        "en": "(manual entry)",
        "pt": "(entrada manual)",
    },
    "calc.ab_source_selected": {
        "en": "Coefficients from selected source",
        "pt": "Coeficientes da fonte selecionada",
    },
    "calc.exact_value": {
        "en": "Full value used in calculation: {value}",
        "pt": "Valor integral usado no cálculo: {value}",
    },
    "calc.apply_class_values": {
        "en": "Apply class values",
        "pt": "Aplicar valores da classe",
    },
    "calc.a_coefficient": {
        "en": "A",
        "pt": "A",
    },
    "calc.b_coefficient": {
        "en": "B",
        "pt": "B",
    },
    "calc.alpha_deg": {
        "en": "Angle α (°)",
        "pt": "Ângulo α (°)",
    },
    "calc.formula_hint": {
        "en": "Deformation energy uses the extended CRASH3 formula, including the angle correction.",
        "pt": "A energia de deformação usa a fórmula estendida do CRASH3, com correção angular.",
    },
    "calc.compute_energy": {
        "en": "Calculate energy",
        "pt": "Calcular energia",
    },
    "calc.compute_energy_and_ees": {
        "en": "Calculate energy and EES",
        "pt": "Calcular energia e EES",
    },
    "calc.view_result": {"en": "View result", "pt": "Ver resultado"},
    "calc.total_energy_default": {
        "en": "Total energy<br><b style='font-size: 16px'>—</b>",
        "pt": "Energia total<br><b style='font-size: 16px'>—</b>",
    },
    "calc.total_energy_value": {
        "en": "Total energy<br><b style='font-size: 16px'>{value} {unit}</b>",
        "pt": "Energia total<br><b style='font-size: 16px'>{value} {unit}</b>",
    },
    "calc.vehicle_mass": {
        "en": "Mass (kg)",
        "pt": "Massa (kg)",
    },
    "calc.mass_hint": {
        "en": "Mass is optional for energy and required for EES.",
        "pt": "Massa opcional para energia e necessária para EES.",
    },
    "calc.technical_details": {"en": "Technical details", "pt": "Detalhes técnicos"},
    "calc.compute_speed": {
        "en": "Calculate EES",
        "pt": "Calcular EES",
    },
    "calc.damage_speed_default": {
        "en": "EES<br><b style='font-size: 16px'>—</b>",
        "pt": "EES<br><b style='font-size: 16px'>—</b>",
    },
    "calc.damage_speed_value": {
        "en": "EES<br><b style='font-size: 16px'>{value} {unit}</b>",
        "pt": "EES<br><b style='font-size: 16px'>{value} {unit}</b>",
    },
    "calc.show_crush_profile": {
        "en": "Crush profile",
        "pt": "Perfil de deformação",
    },
    "calc.dialog.title": {
        "en": "CRASH3",
        "pt": "CRASH3",
    },
    "calc.speed.dialog.title": {
        "en": "Damage Speed",
        "pt": "Velocidade de Dano",
    },
    "calc.profile.dialog.title": {
        "en": "Crush Profile",
        "pt": "Perfil de deformação",
    },
    "calc.error.invalid_ab_alpha": {
        "en": "Check the numbers in A, B and Alpha. Use an unambiguous format, such as 1234.50.",
        "pt": "Confira os números em A, B e Alpha. Use um formato inequívoco, como 1234,50.",
    },
    "calc.error.a_positive": {
        "en": "A must be > 0.",
        "pt": "A deve ser > 0.",
    },
    "calc.error.b_positive": {
        "en": "B must be > 0.",
        "pt": "B deve ser > 0.",
    },
    "calc.error.alpha_range": {
        "en": "Alpha must be between 0 and 89 degrees.",
        "pt": "Alpha deve estar entre 0 e 89 graus.",
    },
    "calc.error.class_not_found": {
        "en": "Selected class not found in stiffness library.",
        "pt": "Classe selecionada não encontrada na biblioteca de rigidez.",
    },
    "calc.error.invalid_vehicle_mass": {
        "en": "Enter a valid, positive vehicle mass in kg, such as 1800 or 1800.50.",
        "pt": "Informe uma massa válida e positiva em kg, como 1800 ou 1800,50.",
    },
    "number.error.rejected": {
        "en": "Number rejected. Check the range, decimal places and separators. The previous value was kept.",
        "pt": "Número rejeitado. Confira a faixa, as casas decimais e os separadores. O valor anterior foi mantido.",
    },
    "number.input_hint": {
        "en": "1.234 is a decimal in English. For one thousand two hundred thirty-four, use 1234 or 1,234.00.",
        "pt": "1,234 é um decimal em português. Para mil duzentos e trinta e quatro, use 1234 ou 1.234,00.",
    },
    "calc.error.invalid_energy_result": {
        "en": "A finite, positive energy value is required.",
        "pt": "É necessário um valor de energia finito e positivo.",
    },
    "calc.error.invalid_speed_result": {
        "en": "The calculation did not produce a valid EES.",
        "pt": "O cálculo não produziu uma EES válida.",
    },
    "profile.window_title": {
        "en": "Crush Profile",
        "pt": "Perfil de deformação",
    },
    "profile.title": {
        "en": "Crush Profile",
        "pt": "Perfil de deformação",
    },
    "profile.subtitle": {
        "en": "Lateral crush profile based on C1-C6 values measured in meters.",
        "pt": "Perfil lateral de deformação com base nos valores C1-C6 medidos em metros.",
    },
    "profile.export_png": {
        "en": "Export Crush Profile PNG",
        "pt": "Exportar Crush Profile PNG",
    },
    "profile.export_dialog_title": {
        "en": "Export Crush Profile PNG",
        "pt": "Exportar Crush Profile PNG",
    },
    "profile.y_axis": {
        "en": "Crush depth (m)",
        "pt": "Profundidade de deformação (m)",
    },
    "profile.x_axis": {
        "en": "Measurement slices",
        "pt": "Slices de medição",
    },
    "profile.error.save_failed": {
        "en": "Failed to save PNG: {path}",
        "pt": "Falha ao salvar PNG: {path}",
    },
    "measurement.measured_distance_value": {
        "en": "Measured distance: (px) {value}",
        "pt": "Distância medida: (px) {value}",
    },
    "measurement.scale_value": {
        "en": "Scale: (m/px) {value}",
        "pt": "Escala: (m/px) {value}",
    },
    "measurement.error.measure_2_points_first": {
        "en": "Measure 2 points first (px distance).",
        "pt": "Meça 2 pontos primeiro (distância em px).",
    },
    "measurement.error.invalid_real_distance": {
        "en": "Enter a valid distance in m, such as 1.234. For thousands, omit grouping or include a decimal part.",
        "pt": "Informe uma distância válida em m, como 1,234. Para milhares, omita o agrupamento ou inclua a parte decimal.",
    },
    "measurement.error.real_distance_positive": {
        "en": "Real distance must be > 0.",
        "pt": "A distância real deve ser > 0.",
    },
    "measurement.warning.unusual_scale": {
        "en": "Scale looks unusual: {value} m/px. Check your points/value.",
        "pt": "A escala parece incomum: {value} m/px. Verifique os pontos/valor.",
    },
    "measurement.w_value_full": {
        "en": "W: {m} m",
        "pt": "W: {m} m",
    },
    "measurement.w_value_px_only": {
        "en": "W: {px} px | - m",
        "pt": "W: {px} px | - m",
    },
    "measurement.delta_w_value_full": {
        "en": "ΔW: {px} px · {m} m",
        "pt": "ΔW: {px} px · {m} m",
    },
    "measurement.delta_w_value_px_only": {
        "en": "ΔW: {px} px · — m",
        "pt": "ΔW: {px} px · — m",
    },
    "measurement.c_values_prefix": {
        "en": "C values (m):",
        "pt": "Valores de C (m):",
    },
    "navigation.resolve_alignment": {
        "en": "Finish or cancel the alignment in progress.",
        "pt": "Conclua ou cancele o alinhamento em andamento.",
    },
    "navigation.load_image": {
        "en": "Load an image before continuing.",
        "pt": "Carregue uma imagem antes de continuar.",
    },
    "navigation.measure_width": {
        "en": "Measure width W before continuing.",
        "pt": "Meça a largura W antes de continuar.",
    },
    "navigation.measure_crush": {
        "en": "Complete measurements C1–C6.",
        "pt": "Complete as medições C1–C6.",
    },
    "workflow.error.apply_calibration_first": {
        "en": "Apply calibration first (m/px).",
        "pt": "Aplique a calibração primeiro (m/px).",
    },
    "workflow.error.incomplete_marking": {
        "en": "Incomplete: need W, scale and all C1..C6.",
        "pt": "Incompleto: é necessário W, escala e todos os C1..C6.",
    },
    "project.new.dialog_title": {
        "en": "New project",
        "pt": "Novo projeto",
    },
    "project.new.prompt_name": {
        "en": "Project name:",
        "pt": "Nome do projeto:",
    },
    "project.new.created": {
        "en": "Project created: {name}",
        "pt": "Projeto criado: {name}",
    },
    "project.save.dialog_title": {
        "en": "Save project",
        "pt": "Salvar projeto",
    },
    "project.load.dialog_title": {
        "en": "Load project",
        "pt": "Carregar projeto",
    },
    "project.load.unsupported_crash3_units": {
        "en": "Cannot load project: unrecognized crash3_units marker {units}. The current project has not been changed.",
        "pt": "Não foi possível carregar o projeto: marcador crash3_units não reconhecido {units}. O projeto atual não foi alterado.",
    },
    "project.save.failed": {
        "en": "Could not save the project: {error}",
        "pt": "Não foi possível salvar o projeto: {error}",
    },
    "project.save.invalid_data": {
        "en": "Could not save the project. {error}\n\nThe destination file was left unchanged.",
        "pt": "Não foi possível salvar o projeto. {error}\n\nO arquivo de destino foi preservado.",
    },
    "project.load.failed": {
        "en": "Could not open the project: {error}",
        "pt": "Não foi possível abrir o projeto: {error}",
    },
    "project.load.invalid_structure": {
        "en": "The JSON root must be an object.",
        "pt": "O JSON deve conter um objeto na raiz.",
    },
    "project.load.invalid_data": {
        "en": "Could not open the project. {error}\n\nThe file and the current project were left unchanged.",
        "pt": "Não foi possível abrir o projeto. {error}\n\nO arquivo e o projeto atual foram preservados.",
    },
    "project.data.invalid_number": {
        "en": "The field {field} must contain a finite number. Stored value: {value}.",
        "pt": "O campo {field} deve conter um número finito. Valor gravado: {value}.",
    },
    "project.data.positive_number": {
        "en": "The field {field} must be greater than zero. Stored value: {value}.",
        "pt": "O campo {field} deve ser maior que zero. Valor gravado: {value}.",
    },
    "project.data.nonnegative_number": {
        "en": "The field {field} cannot be negative. Stored value: {value}.",
        "pt": "O campo {field} não pode ser negativo. Valor gravado: {value}.",
    },
    "project.data.out_of_range": {
        "en": "The field {field} must satisfy {minimum} <= value {upper_bound} {maximum}. Stored value: {value}.",
        "pt": "O campo {field} deve satisfazer {minimum} <= valor {upper_bound} {maximum}. Valor gravado: {value}.",
    },
    "project.data.invalid_field": {
        "en": "The field {field} has an invalid structure or identifier.",
        "pt": "O campo {field} contém uma estrutura ou um identificador inválido.",
    },
    "project.data.duplicate_key": {
        "en": "The JSON key {field} is repeated in the same object.",
        "pt": "A chave JSON {field} aparece mais de uma vez no mesmo objeto.",
    },
    "project.data.shared_scale_mismatch": {
        "en": "No common scale fits the stored measurements in pixels and meters. The {field} measurement conflicts with the available scale or other measurements.",
        "pt": "Nenhuma escala comum é compatível com as medições gravadas em pixels e metros. A medição de {field} diverge da escala disponível ou das demais medições.",
    },
    "project.data.slice_spacing_mismatch": {
        "en": "The six stored slice positions are incompatible with five equal W/5 intervals.",
        "pt": "As seis posições de fatias gravadas são incompatíveis com cinco intervalos iguais de W/5.",
    },
    "project.data.image_unavailable": {
        "en": "Could not read the image {field}. Check that the file exists, is accessible and is a valid image.",
        "pt": "Não foi possível ler a imagem {field}. Confira se o arquivo existe, está acessível e é uma imagem válida.",
    },
    "project.data.image_is_save_destination": {
        "en": "The destination {field} is an image referenced by the project. Choose a different file.",
        "pt": "O destino {field} é uma imagem referenciada pelo projeto. Escolha outro arquivo.",
    },
    "project.data.width_interval_mismatch": {
        "en": "The stored interval {field} ({value}) disagrees with W/5 ({expected}).",
        "pt": "O intervalo gravado {field} ({value}) é incompatível com W/5 ({expected}).",
    },
    "project.data.ees_units_mismatch": {
        "en": "The stored EES values disagree: {mps} m/s and {kmh} km/h.",
        "pt": "Os valores gravados de EES são incompatíveis: {mps} m/s e {kmh} km/h.",
    },
    "project.data.energy_mismatch": {
        "en": "The stored energy ({value} J) is inconsistent with the CRASH3 inputs (calculated value: {expected} J).",
        "pt": "A energia gravada ({value} J) é incompatível com os parâmetros CRASH3 (valor calculado: {expected} J).",
    },
    "project.data.ees_energy_mismatch": {
        "en": "The stored EES ({field} = {value}) is inconsistent with the stored energy ({energy} J) and mass ({mass} kg).",
        "pt": "A EES gravada ({field} = {value}) é incompatível com a energia ({energy} J) e a massa ({mass} kg) gravadas.",
    },
    "project.load.images_failed": {
        "en": "Cannot load project: failed to read image {error}. The current project has not been changed.",
        "pt": "Não foi possível carregar o projeto: falha ao ler a imagem {error}. O projeto atual não foi alterado.",
    },
    "project.load.loaded": {
        "en": "Loaded: {path}",
        "pt": "Carregado: {path}",
    },
    "project.export_png.dialog_title": {
        "en": "Export annotated image",
        "pt": "Exportar imagem anotada",
    },
    "project.export_png.saved": {
        "en": "PNG exported: {path}",
        "pt": "PNG exportado: {path}",
    },
    "project.export_png.failed": {
        "en": "Could not save the PNG at {path}. Check that the folder exists, that you have write permission, and that the file is not in use.\n\nDetails: {error}",
        "pt": "Não foi possível gravar o PNG em {path}. Confira se a pasta existe, se você tem permissão de gravação e se o arquivo está fechado em outros programas.\n\nDetalhes: {error}",
    },
    "project.export_current_view.dialog_title": {
        "en": "Export current view",
        "pt": "Exportar visualização atual",
    },
    "project.export_current_view.saved": {
        "en": "Current view exported: {path}",
        "pt": "Visualização atual exportada: {path}",
    },
    "project.export_current_view.capture_failed": {
        "en": "The current view could not be captured.",
        "pt": "Não foi possível capturar a visualização atual.",
    },
    "project.select_image.dialog_title": {
        "en": "Select image",
        "pt": "Selecionar imagem",
    },
    "project.replace_image.dialog_title": {
        "en": "Replace image",
        "pt": "Substituir imagem",
    },
    "project.replace_image.confirm_reset": {
        "en": "Loading a new image will reset alignment, calibration, markings and calculated results.\n\nDo you want to continue?",
        "pt": "Carregar uma nova imagem irá resetar alinhamento, calibração, marcações e resultados calculados.\n\nDeseja continuar?",
    },
    "project.load_ref.error_title": {
        "en": "Error loading reference",
        "pt": "Erro ao carregar referência",
    },
    "project.load_dam.error_title": {
        "en": "Error loading the damaged vehicle image",
        "pt": "Erro ao carregar a imagem do veículo danificado",
    },
    "summary.project": {
        "en": "Project: {name}",
        "pt": "Projeto: {name}",
    },
    "summary.stage": {
        "en": "Stage: {stage}",
        "pt": "Etapa: {stage}",
    },
    "summary.single_image_active": {
        "en": "Single image mode active",
        "pt": "Modo de imagem única ativo",
    },
    "summary.scale_not_set": {
        "en": "Scale: NOT SET (m/px)",
        "pt": "Escala: NÃO DEFINIDA (m/px)",
    },
    "summary.scale_value": {
        "en": "Scale: {value} m/px",
        "pt": "Escala: {value} m/px",
    },
    "summary.w_not_set": {
        "en": "W: NOT SET",
        "pt": "W: NÃO DEFINIDO",
    },
    "summary.w_value_px_only": {
        "en": "W: {px} px",
        "pt": "W: {px} px",
    },
    "summary.w_value_full": {
        "en": "W: {px} px | {m} m",
        "pt": "W: {px} px | {m} m",
    },
    "summary.c_measures": {
        "en": "C measures: {done}/6",
        "pt": "Medidas C: {done}/6",
    },
    "summary.total_energy_default": {
        "en": "Total Energy: -",
        "pt": "Energia Total: -",
    },
    "summary.total_energy_value": {
        "en": "Total Energy: {value} J",
        "pt": "Energia Total: {value} J",
    },
    "summary.vehicle_mass_default": {
        "en": "Vehicle mass: -",
        "pt": "Massa do veículo: -",
    },
    "summary.vehicle_mass_value": {
        "en": "Vehicle mass: {value} kg",
        "pt": "Massa do veículo: {value} kg",
    },
    "summary.damage_speed_default": {
        "en": "Damage Speed: -",
        "pt": "Velocidade de Dano: -",
    },
    "summary.damage_speed_value": {
        "en": "Damage Speed: {value} km/h",
        "pt": "Velocidade de Dano: {value} km/h",
    },
    "summary.status_complete": {
        "en": "Status: complete",
        "pt": "Status: completo",
    },
    "summary.status_incomplete": {
        "en": "Status: incomplete",
        "pt": "Status: incompleto",
    },
    "stage.load": {
        "en": "load",
        "pt": "carregamento",
    },
    "stage.alignment": {
        "en": "alignment",
        "pt": "alinhamento",
    },
    "stage.calibration": {
        "en": "calibration",
        "pt": "calibração",
    },
    "stage.marking": {
        "en": "marking",
        "pt": "marcação",
    },
    "stage.done": {
        "en": "done",
        "pt": "concluído",
    },
    "alignment.warning.title": {
        "en": "Calibration warning",
        "pt": "Aviso de calibração",
    },
    "alignment.warning.scale_mismatch": {
        "en": "The reference image and the damaged vehicle image currently have different visual scales.\n\nCalibration may become inconsistent unless both vehicles are visually matched in size before calibration.\n\nContinue anyway?",
        "pt": "A imagem de referência e a imagem do veículo danificado estão atualmente com escalas visuais diferentes.\n\nA calibração pode ficar inconsistente se ambos os veículos não estiverem visualmente compatíveis em tamanho antes da calibração.\n\nDeseja continuar mesmo assim?",
    },
    "report.units": {
        "en": "Units",
        "pt": "Unidades",
    },
    "marking.measure_w": {
        "en": "Measure W",
        "pt": "Medir W",
    },
    "marking.set_w_mode": {
        "en": "Set W mode",
        "pt": "Modo definir W",
    },
    "marking.generate_slices": {
        "en": "Generate 6 slices",
        "pt": "Gerar 6 divisões",
    },
    "marking.select_c": {
        "en": "Select C to edit",
        "pt": "Selecionar C para editar",
    },
    "marking.restart_marking": {
        "en": "Restart marking",
        "pt": "Reiniciar marcação",
    },
    "alignment.nudge": {
        "en": "Nudge (px)",
        "pt": "Ajuste fino (px)",
    },
    "alignment.rotate": {
        "en": "Rotate",
        "pt": "Rotação",
    },
    "alignment.scale": {
        "en": "Scale",
        "pt": "Escala",
    },
    "alignment.step_px": {
        "en": "Step (px)",
        "pt": "Passo (px)",
    },
    "alignment.apply": {
        "en": "Apply",
        "pt": "Aplicar",
    },
    "report.ab_source": {
        "en": "A/B SOURCE",
        "pt": "ORIGEM DE A/B",
    },
    "report.ab_source_type": {
        "en": "Source type",
        "pt": "Tipo de origem",
    },
    "report.ab_source_label": {
        "en": "Source label",
        "pt": "Rótulo da origem",
    },
    "report.ab_source_ref": {
        "en": "Source reference",
        "pt": "Referência da origem",
    },
    "msg.warning": {
        "en": "Warning",
        "pt": "Aviso",
    },
    "msg.invalid_ab": {
        "en": "Invalid A/B values.",
        "pt": "Valores de A/B inválidos.",
    },
    "msg.ab_positive": {
        "en": "A and B must be positive.",
        "pt": "A e B devem ser positivos.",
    },
    "msg.ab_range": {
        "en": "A/B values out of expected range.",
        "pt": "Valores de A/B fora do intervalo esperado.",
    },
    "dialog.select_ab_title": {
        "en": "Select NHTSA A/B record",
        "pt": "Selecionar registro A/B NHTSA",
    },
    "dialog.select_ab_label": {
        "en": "Record:",
        "pt": "Registro:",
    },
    "calc.ab_source_default": {
        "en": "A/B source not specified",
        "pt": "Origem de A/B não informada",
    },
    "calc.ab_source_nhtsa": {
        "en": "A/B source: NHTSA library{label}",
        "pt": "Origem de A/B: Biblioteca NHTSA{label}",
    },
    "calc.ab_source_generic": {
        "en": "A/B source: Generic class{label}",
        "pt": "Origem de A/B: Classe genérica{label}",
    },
    "calc.ab_source_manual": {
        "en": "A/B source: Manual entry",
        "pt": "Origem de A/B: Entrada manual",
    },
    "calc.load_ab_nhtsa": {
        "en": "Load A/B (NHTSA)",
        "pt": "Carregar A/B (NHTSA)",
    },
    "calc.save_ab_nhtsa": {
        "en": "Save A/B (NHTSA)",
        "pt": "Salvar A/B (NHTSA)",
    },
    "calc.library_empty": {
        "en": "Library is empty.",
        "pt": "A biblioteca está vazia.",
    },
    "calc.library_no_valid_ab": {
        "en": "No records with valid A/B were found.",
        "pt": "Nenhum registro com A/B válido foi encontrado.",
    },
    "calc.saved_to_library": {
        "en": "A/B saved to library.",
        "pt": "A/B salvo na biblioteca.",
    },
    "msg.error": {
        "en": "Error",
        "pt": "Erro",
    },
    "msg.success": {
        "en": "Success",
        "pt": "Sucesso",
    },
    "calc.ab.test_speed_used": {
        "en": "Speed used for A/B (km/h)",
        "pt": "Velocidade usada para A/B (km/h)",
    },
    "calc.ab.test_angle": {"en": "Test angle (°)", "pt": "Ângulo do ensaio (°)"},
    "calc.ab.test_mass": {"en": "Test mass (kg)", "pt": "Massa do ensaio (kg)"},
    "calc.ab.test_crush": {"en": "Test crush (m)", "pt": "Deformações do ensaio (m)"},
    "calc.ab.overlap": {"en": "Overlap (%)", "pt": "Sobreposição (%)"},
    "calc.ab.notes": {"en": "Notes", "pt": "Observações"},
    "nhtsa.dialog.title": {
        "en": "Compute A/B from NHTSA report",
        "pt": "Calcular A/B a partir de relatório NHTSA",
    },
    "nhtsa.group.identification": {
        "en": "Test identification",
        "pt": "Identificação do teste",
    },
    "nhtsa.group.inputs": {
        "en": "Test inputs",
        "pt": "Entradas do teste",
    },
    "nhtsa.group.crush": {
        "en": "Crush values",
        "pt": "Valores de deformação",
    },
    "nhtsa.group.outputs": {
        "en": "Computed outputs",
        "pt": "Saídas calculadas",
    },
    "nhtsa.field.test_agency": {
        "en": "Test agency",
        "pt": "Agência do teste",
    },
    "nhtsa.field.test_number": {
        "en": "Test number",
        "pt": "Número do teste",
    },
    "nhtsa.field.report_number": {
        "en": "Report number",
        "pt": "Número do relatório",
    },
    "nhtsa.field.make": {
        "en": "Make",
        "pt": "Marca",
    },
    "nhtsa.field.model": {
        "en": "Model",
        "pt": "Modelo",
    },
    "nhtsa.field.year": {
        "en": "Year",
        "pt": "Ano",
    },
    "nhtsa.field.test_type": {
        "en": "Test type",
        "pt": "Tipo de teste",
    },
    "nhtsa.field.test_configuration": {
        "en": "Test configuration",
        "pt": "Configuração do teste",
    },
    "nhtsa.field.barrier_type": {
        "en": "Barrier type",
        "pt": "Tipo de barreira",
    },
    "nhtsa.field.overlap_pct": {
        "en": "Overlap (%)",
        "pt": "Overlap (%)",
    },
    "nhtsa.field.impact_direction": {
        "en": "Impact direction",
        "pt": "Direção do impacto",
    },
    "nhtsa.field.test_label": {
        "en": "Test label",
        "pt": "Rótulo do teste",
    },
    "nhtsa.field.test_speed_mps": {
        "en": "Test speed (m/s)",
        "pt": "Velocidade do teste (m/s)",
    },
    "nhtsa.field.impact_angle_deg": {
        "en": "Impact angle (deg)",
        "pt": "Ângulo do impacto (graus)",
    },
    "nhtsa.field.vehicle_mass_kg": {
        "en": "Vehicle mass (kg)",
        "pt": "Massa do veículo (kg)",
    },
    "nhtsa.field.b0_mps": {
        "en": "b0 (m/s)",
        "pt": "b0 (m/s)",
    },
    "nhtsa.field.L_m": {
        "en": "L (m)",
        "pt": "L (m)",
    },
    "nhtsa.output.crush_area_m2": {
        "en": "Crush area (m²)",
        "pt": "Área de deformação (m²)",
    },
    "nhtsa.output.c_mean_m": {
        "en": "Mean crush (m)",
        "pt": "Deformação média (m)",
    },
    "nhtsa.output.b1_per_s": {
        "en": "b1 (1/s)",
        "pt": "b1 (1/s)",
    },
    "nhtsa.output.A_n_per_m": {
        "en": "A (N/m)",
        "pt": "A (N/m)",
    },
    "nhtsa.output.B_n_per_m2": {
        "en": "B (N/m²)",
        "pt": "B (N/m²)",
    },
    "nhtsa.button.compute": {
        "en": "Compute",
        "pt": "Calcular",
    },
    "nhtsa.button.apply": {
        "en": "Apply A/B to current project",
        "pt": "Aplicar A/B ao projeto atual",
    },
    "nhtsa.button.save": {
        "en": "Save to NHTSA library",
        "pt": "Salvar na biblioteca NHTSA",
    },
    "nhtsa.button.cancel": {
        "en": "Cancel",
        "pt": "Cancelar",
    },
    "nhtsa.test_type.frontal": {
        "en": "Frontal",
        "pt": "Frontal",
    },
    "nhtsa.test_type.side": {
        "en": "Side",
        "pt": "Lateral",
    },
    "nhtsa.test_type.rear": {
        "en": "Rear",
        "pt": "Traseiro",
    },
    "nhtsa.config.rigid_frontal_barrier": {
        "en": "Rigid Frontal Barrier",
        "pt": "Barreira Frontal Rígida",
    },
    "nhtsa.config.deformable_offset_barrier": {
        "en": "Deformable Offset Barrier",
        "pt": "Barreira Deformável com Offset",
    },
    "nhtsa.config.rigid_angled_barrier": {
        "en": "Rigid Angled Barrier",
        "pt": "Barreira Rígida Angulada",
    },
    "nhtsa.config.side_moving_deformable_barrier": {
        "en": "Side Moving Deformable Barrier",
        "pt": "Barreira Deformável Móvel Lateral",
    },
    "nhtsa.config.rigid_pole_side_impact": {
        "en": "Rigid Pole Side Impact",
        "pt": "Impacto Lateral em Poste Rígido",
    },
    "nhtsa.config.rear_rigid_barrier": {
        "en": "Rear Rigid Barrier",
        "pt": "Barreira Traseira Rígida",
    },
    "nhtsa.config.rear_deformable_barrier": {
        "en": "Rear Deformable Barrier",
        "pt": "Barreira Traseira Deformável",
    },
    "nhtsa.barrier_type.rigid": {
        "en": "Rigid",
        "pt": "Rígida",
    },
    "nhtsa.barrier_type.deformable": {
        "en": "Deformable",
        "pt": "Deformável",
    },
    "nhtsa.barrier_type.pole": {
        "en": "Pole",
        "pt": "Poste",
    },
    "nhtsa.direction.front": {
        "en": "Front",
        "pt": "Frontal",
    },
    "nhtsa.direction.side": {
        "en": "Side",
        "pt": "Lateral",
    },
    "nhtsa.direction.rear": {
        "en": "Rear",
        "pt": "Traseiro",
    },
    "nhtsa.error.compute_first": {
        "en": "Compute A/B first.",
        "pt": "Calcule A/B primeiro.",
    },
    "nhtsa.error.c_gt_L": {
        "en": "Crush values (C1..C6) cannot exceed the damaged width L.",
        "pt": "Os valores de deformação (C1..C6) não podem exceder a largura danificada L.",
    },
    "nhtsa.saved_to_library": {
        "en": "Record saved to NHTSA library.",
        "pt": "Registro salvo na biblioteca NHTSA.",
    },
    "calc.compute_ab_from_nhtsa": {
        "en": "A/B from NHTSA",
        "pt": "A/B via NHTSA",
    },
    "calc.ab_source_nhtsa_report": {
        "en": "A/B source: NHTSA report{label}",
        "pt": "Origem de A/B: Relatório NHTSA{label}",
    },
    "report.ab_source_reference": {
        "en": "Source document",
        "pt": "Documento de origem",
    },
    "calc.edit_ab_from_nhtsa": {
        "en": "Edit NHTSA",
        "pt": "Editar NHTSA",
    },
    "calc.no_nhtsa_snapshot": {
        "en": "No saved NHTSA input data in current project.",
        "pt": "Não há dados salvos de entrada NHTSA no projeto atual.",
    },
    "nhtsa.auto_test_label": {
        "en": "{config} | {speed} | {angle} | overlap {overlap}",
        "pt": "{config} | {speed} | {angle} | overlap {overlap}",
    },
    "nhtsa.error.invalid_L": {
        "en": "L must be greater than zero.",
        "pt": "L deve ser maior que zero.",
    },
    "nhtsa.error.invalid_mass": {
        "en": "Vehicle mass must be greater than zero.",
        "pt": "A massa do veículo deve ser maior que zero.",
    },
    "nhtsa.error.invalid_speed": {
        "en": "Test speed must be greater than zero.",
        "pt": "A velocidade do teste deve ser maior que zero.",
    },
    "nhtsa.error.invalid_c_values": {
        "en": "All C1..C6 values must be zero or greater.",
        "pt": "Todos os valores de C1..C6 devem ser maiores ou iguais a zero.",
    },
    "nhtsa.field.c_value": {
        "en": "C{index} (m)",
        "pt": "C{index} (m)",
    },
    "nhtsa.overlap.na": {
        "en": "N/A",
        "pt": "N/A",
    },
    "nhtsa.error.all_c_zero": {
        "en": "All crush values are zero.",
        "pt": "Todos os valores de deformação são zero.",
    },
    "nhtsa.error.speed_out_of_range": {
        "en": "Test speed is outside the typical NHTSA range (1 to 40 m/s).",
        "pt": "A velocidade do teste está fora da faixa típica da NHTSA (1 a 40 m/s).",
    },
    "nhtsa.error.mass_out_of_range": {
        "en": "Vehicle mass is outside the plausible range (300 to 4000 kg).",
        "pt": "A massa do veículo está fora da faixa plausível (300 a 4000 kg).",
    },
    "calc.group.source": {
        "en": "A/B coefficients",
        "pt": "Coeficientes A/B",
    },
    "calc.group.params": {
        "en": "Parameters",
        "pt": "Parâmetros",
    },
    "calc.group.calc": {
        "en": "Run calculation",
        "pt": "Execução do cálculo",
    },
    "project.untitled": {
        "en": "untitled",
        "pt": "sem_titulo",
    },
    "calc.ab_menu": {
        "en": "Library: A/B files...",
        "pt": "Biblioteca: Arquivos A/B...",
    },
    "calc.ab_list.test": {
        "en": "test",
        "pt": "teste",
    },
    "calc.ab_list.report": {
        "en": "report",
        "pt": "relatório",
    },
    "calc.ab_menu.load_library": {
        "en": "Load from NHTSA library",
        "pt": "Carregar da biblioteca NHTSA",
    },
    "calc.ab_menu.import_file": {
        "en": "Import A/B file (.json)",
        "pt": "Importar arquivo A/B (.json)",
    },
    "calc.ab_menu.export_file": {
        "en": "Export current A/B (.json)",
        "pt": "Exportar A/B atual (.json)",
    },
    "calc.ab_file.not_implemented": {
        "en": "This action is not implemented yet.",
        "pt": "Esta ação ainda não foi implementada.",
    },
    "calc.ab_file.import_title": {
        "en": "Import A/B file",
        "pt": "Importar arquivo A/B",
    },
    "calc.ab_file.export_title": {
        "en": "Export current A/B",
        "pt": "Exportar A/B atual",
    },
    "calc.ab_file.invalid": {
        "en": "Invalid A/B file.",
        "pt": "Arquivo A/B inválido.",
    },
    "calc.ab_file.exported": {
        "en": "A/B file exported successfully.",
        "pt": "Arquivo A/B exportado com sucesso.",
    },
    "calc.ab_source_nhtsa_file": {
        "en": "A/B source: A/B file{label}",
        "pt": "Origem de A/B: Arquivo A/B{label}",
    },
    "report.bumper_offset_m": {
        "en": "Offset to bumper crossmember (m)",
        "pt": "Offset até a travessa do para-choque (m)",
    },
    "label.bumper_offset_m": {
        "en": "Bumper crossmember offset (m)",
        "pt": "Offset da travessa (m)",
    },
    "nhtsa.field.impact_speed_mps": {
        "en": "Impact speed (km/h)",
        "pt": "Velocidade de impacto (km/h)",
    },
    "nhtsa.field.velocity_change_mps": {
        "en": "Test velocity change (km/h)",
        "pt": "Variação de velocidade do teste (km/h)",
    },
    "nhtsa.group.derived_speeds": {
        "en": "Derived speeds",
        "pt": "Velocidades derivadas",
    },
    "nhtsa.output.rebound_speed_mps": {
        "en": "Rebound speed (km/h)",
        "pt": "Velocidade de restituição (km/h)",
    },
    "nhtsa.output.damage_speed_mps": {
        "en": "Damage speed (km/h)",
        "pt": "Velocidade de danos (km/h)",
    },
    "nhtsa.field.speed_basis": {
        "en": "Speed basis for A/B",
        "pt": "Base de velocidade para A/B",
    },
    "nhtsa.speed_basis.impact": {
        "en": "Use impact speed",
        "pt": "Usar velocidade de impacto",
    },
    "nhtsa.speed_basis.damage": {
        "en": "Use damage speed",
        "pt": "Usar velocidade de danos",
    },
    "nhtsa.error.invalid_impact_speed": {
        "en": "Impact speed must be greater than zero.",
        "pt": "A velocidade de impacto deve ser maior que zero.",
    },
    "nhtsa.error.invalid_velocity_change": {
        "en": "Velocity change must be greater than zero.",
        "pt": "A variação de velocidade deve ser maior que zero.",
    },
    "nhtsa.error.impact_speed_out_of_range": {
        "en": "Impact speed appears outside the expected range.",
        "pt": "A velocidade de impacto parece estar fora da faixa esperada.",
    },
    "nhtsa.error.velocity_change_out_of_range": {
        "en": "Velocity change appears outside the expected range.",
        "pt": "A variação de velocidade parece estar fora da faixa esperada.",
    },
    "nhtsa.error.velocity_change_lt_impact": {
        "en": "Velocity change must be greater than or equal to impact speed.",
        "pt": "A variação de velocidade deve ser maior ou igual à velocidade de impacto.",
    },
    "report.method.nhtsa_file": {
        "en": "Imported from A/B file",
        "pt": "Importado de arquivo A/B",
    },
    "report.impact_speed_mps": {
        "en": "Impact speed (m/s)",
        "pt": "Velocidade de impacto (m/s)",
    },
    "report.velocity_change_mps": {
        "en": "Test velocity change (m/s)",
        "pt": "Variação de velocidade do teste (m/s)",
    },
    "report.rebound_speed_mps": {
        "en": "Rebound speed (m/s)",
        "pt": "Velocidade de restituição (m/s)",
    },
    "report.speed_used_mps": {
        "en": "Speed used for A/B (m/s)",
        "pt": "Velocidade usada para A/B (m/s)",
    },
    "report.speed_basis": {
        "en": "Speed basis for A/B",
        "pt": "Base de velocidade para A/B",
    },
    "report.ees.unavailable": {
        "en": "EES unavailable. The project has no recorded speed.",
        "pt": "EES indisponível. O projeto não tem velocidade gravada.",
    },
    "report.ees.mass_required": {
        "en": "EES unavailable. Calculating it requires the vehicle mass.",
        "pt": "EES indisponível. O cálculo requer a massa do veículo.",
    },
    "report.ees.mass_not_recorded": {
        "en": "The project records an EES but does not document the mass used.",
        "pt": "O projeto registra a EES, mas não documenta a massa utilizada.",
    },
    "report.ees.converted_from_kmh": {
        "en": "converted from stored km/h",
        "pt": "convertida do valor gravado em km/h",
    },
    "report.ees.converted_from_mps": {
        "en": "converted from stored m/s",
        "pt": "convertida do valor gravado em m/s",
    },
    "alignment.single_image.title": {
        "en": "Single image",
        "pt": "Imagem única",
    },
    "alignment.single_image.confirm": {
        "en": (
            "Only one image was loaded. "
            "Do you want to continue without overlaying two images?\n\n"
            "Calibration and marking will be performed directly "
            "on the loaded image."
        ),
        "pt": (
            "Apenas uma imagem foi carregada. "
            "Deseja continuar sem sobreposição de duas imagens?\n\n"
            "A calibração e as marcações serão realizadas "
            "diretamente sobre a imagem carregada."
        ),
    },
}


def set_language(lang: str) -> None:
    global LANG
    LANG = lang if lang in {"en", "pt"} else "en"


def get_language() -> str:
    return LANG


def tr(key: str, **kwargs) -> str:
    entry = STRINGS.get(key)
    if not entry:
        text = key
    else:
        text = entry.get(LANG, entry.get("en", key))
    if kwargs:
        return text.format(**kwargs)
    return text
