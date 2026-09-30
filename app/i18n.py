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
    "menu.new": {
        "en": "New",
        "pt": "Novo",
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
        "en": "Export overlay PNG",
        "pt": "Exportar overlay PNG",
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
        "pt": "Inglês",
    },
    "menu.language.portuguese": {
        "en": "Português",
        "pt": "Português",
    },
    "dock.controls": {
        "en": "Controls",
        "pt": "Controles",
    },
    "group.load_images": {
        "en": "Load images",
        "pt": "Carregar imagens",
    },
    "button.load_ref": {
        "en": "Load reference image (ref)",
        "pt": "Carregar imagem de referência (ref)",
    },
    "button.load_dam": {
        "en": "Load deformed image (dam)",
        "pt": "Carregar imagem deformada (dam)",
    },
    "label.overlay_opacity": {
        "en": "Overlay opacity",
        "pt": "Opacidade do overlay",
    },
    "group.alignment": {
        "en": "Alignment",
        "pt": "Alinhamento",
    },
    "check.alignment_mode": {
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
        "en": "Deformed",
        "pt": "Deformada",
    },
    "combo.reference": {
        "en": "Reference",
        "pt": "Referência",
    },
    "button.reset_selected_transform": {
        "en": "Reset image transforms",
        "pt": "Resetar transformações das imagens",
    },
    "group.nudge": {
        "en": "Nudge (px)",
        "pt": "Ajuste fino (px)",
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
        "en": "Step (deg):",
        "pt": "Passo (graus):",
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
        "en": "Step (%):",
        "pt": "Passo (%):",
    },
    "label.alignment_shortcuts": {
        "en": "Shortcuts: arrows = nudge | Q/E = rotate | Z/X = scale",
        "pt": "Atalhos: setas = ajuste fino | Q/E = rotacionar | Z/X = escala",
    },
    "button.finish_alignment": {
        "en": "Finish alignment →",
        "pt": "Concluir alinhamento →",
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
    "button.apply_calibration": {
        "en": "Apply calibration",
        "pt": "Aplicar calibração",
    },
    "label.scale_m_per_px": {
        "en": "Scale: (m/px) -",
        "pt": "Escala: (m/px) -",
    },
    "button.confirm_calibration": {
        "en": "Confirm calibration →",
        "pt": "Confirmar calibração →",
    },
    "group.marking": {
        "en": "Marking (W + C1..C6)",
        "pt": "Marcação (W + C1..C6)",
    },
    "check.set_w_mode": {
        "en": "Set W mode (click 2 points: left/right)",
        "pt": "Modo definir W (2 cliques: esquerda/direita)",
    },
    "label.w_default": {
        "en": "W: - px | - m",
        "pt": "W: - px | - m",
    },
    "button.generate_slices": {
        "en": "Generate 6 slices (equidistant)",
        "pt": "Gerar 6 slices (equidistantes)",
    },
    "label.delta_w_default": {
        "en": "Δw: - px | - m",
        "pt": "Δw: - px | - m",
    },
    "check.set_guide_mode": {
        "en": "Set guide line mode (click to place horizontal guide)",
        "pt": "Modo linha-guia (clique para posicionar guia horizontal)",
    },
    "check.measure_ci_mode": {
        "en": "Measure Ci mode (2 clicks per Ci)",
        "pt": "Modo medir Ci (2 cliques por Ci)",
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
        "en": "Finish marking ✓",
        "pt": "Concluir marcação ✓",
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
    "group.summary": {
        "en": "Summary",
        "pt": "Resumo",
    },
    "summary.status_default": {
        "en": "Status: -",
        "pt": "Status: -",
    },
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
        "en": "CRASH3-MVP - EXAM REPORT",
        "pt": "CRASH3-MVP - RELATÓRIO DO EXAME",
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
        "en": "RESULTS",
        "pt": "RESULTADOS",
    },
    "report.project": {
        "en": "Project",
        "pt": "Projeto",
    },
    "report.datetime": {
        "en": "Date/time",
        "pt": "Data/hora",
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
        "en": "Damage speed (m/s)",
        "pt": "Velocidade de dano (m/s)",
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
    "report.si_units_full": {
        "en": "Unit system: SI (N/m, N/m², m, s)",
        "pt": "Sistema de unidades: SI (N/m, N/m², m, s)",
    },
    "report.ab_source_full": {
        "en": "RIGIDITY COEFFICIENT SOURCE (A/B)",
        "pt": "ORIGEM DOS COEFICIENTES DE RIGIDEZ (A/B)",
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
        "en": "Test / reference description",
        "pt": "Descrição do ensaio / referência",
    },
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
        "pt": "Overlap (%)",
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
        "en": "METHODOLOGY",
        "pt": "METODOLOGIA",
    },
    "report.methodology.energy": {
        "en": (
            "Deformation energy was estimated using the CRASH3 model, "
            "based on stiffness coefficients A and B and the measured "
            "crush values (C1 to C6) extracted from the calibrated image."
        ),
        "pt": (
            "A energia de deformação foi estimada utilizando o modelo CRASH3, "
            "com base nos parâmetros de rigidez A e B e nas deformações medidas "
            "(C1 a C6) extraídas da imagem calibrada."
        ),
    },
    "report.methodology.speed": {
        "en": (
            "Damage speed was obtained from the calculated energy and the "
            "vehicle mass considered in the computation."
        ),
        "pt": (
            "A velocidade de dano foi obtida a partir da energia calculada e da "
            "massa do veículo considerada no cálculo."
        ),
    },
    "report.total_energy_deformation_j": {
        "en": "Total deformation energy (J)",
        "pt": "Energia total de deformação (J)",
    },
    "report.vehicle_mass_considered_kg": {
        "en": "Vehicle mass considered (kg)",
        "pt": "Massa do veículo considerada (kg)",
    },
    "report.damage_speed_estimated": {
        "en": "Estimated damage speed",
        "pt": "Velocidade de dano estimada",
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
    "calc.apply_class_values": {
        "en": "Apply class values",
        "pt": "Aplicar valores da classe",
    },
    "calc.a_coefficient": {
        "en": "A coefficient",
        "pt": "Coeficiente A",
    },
    "calc.b_coefficient": {
        "en": "B coefficient",
        "pt": "Coeficiente B",
    },
    "calc.alpha_deg": {
        "en": "Alpha (deg)",
        "pt": "Alpha (graus)",
    },
    "calc.formula_hint": {
        "en": "Extended formula. Units: A in N/m, B in N/m², alpha in degrees.",
        "pt": "Fórmula estendida. Unidades: A em N/m, B em N/m², alpha em graus.",
    },
    "calc.compute_energy": {
        "en": "Compute CRASH3 Energy",
        "pt": "Calcular energia CRASH3",
    },
    "calc.total_energy_default": {
        "en": "<b>Total Energy:</b> -",
        "pt": "<b>Energia Total:</b> -",
    },
    "calc.total_energy_value": {
        "en": "<b>Total Energy:</b> <b>{value} {unit}</b>",
        "pt": "<b>Energia Total:</b> <b>{value} {unit}</b>",
    },
    "calc.vehicle_mass": {
        "en": "Vehicle mass (kg)",
        "pt": "Massa do veículo (kg)",
    },
    "calc.compute_speed": {
        "en": "Compute Damage Speed",
        "pt": "Calcular velocidade de dano",
    },
    "calc.damage_speed_default": {
        "en": "<b>Damage Speed:</b> -",
        "pt": "<b>Velocidade de Dano:</b> -",
    },
    "calc.damage_speed_value": {
        "en": "<b>Damage Speed:</b> <b>{value} {unit}</b>",
        "pt": "<b>Velocidade de Dano:</b> <b>{value} {unit}</b>",
    },
    "calc.show_crush_profile": {
        "en": "Show Crush Profile",
        "pt": "Mostrar perfil de danos",
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
        "en": "Enter valid numeric values for A, B and Alpha.",
        "pt": "Informe valores numéricos válidos para A, B e Alpha.",
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
        "en": "Enter a valid vehicle mass in kg.",
        "pt": "Informe uma massa de veículo válida em kg.",
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
        "en": "Enter a valid real distance in m.",
        "pt": "Informe uma distância real válida em m.",
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
        "en": "W: {px} px | {m} m",
        "pt": "W: {px} px | {m} m",
    },
    "measurement.w_value_px_only": {
        "en": "W: {px} px | - m",
        "pt": "W: {px} px | - m",
    },
    "measurement.delta_w_value_full": {
        "en": "Δw: {px} px | {m} m",
        "pt": "Δw: {px} px | {m} m",
    },
    "measurement.delta_w_value_px_only": {
        "en": "Δw: {px} px | - m",
        "pt": "Δw: {px} px | - m",
    },
    "measurement.c_values_prefix": {
        "en": "C values (m):",
        "pt": "Valores de C (m):",
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
    "project.load.images_failed": {
        "en": "Cannot load project: failed to read image {error}. The current project has not been changed.",
        "pt": "Não foi possível carregar o projeto: falha ao ler a imagem {error}. O projeto atual não foi alterado.",
    },
    "project.load.loaded": {
        "en": "Loaded: {path}",
        "pt": "Carregado: {path}",
    },
    "project.export_png.dialog_title": {
        "en": "Export overlay PNG",
        "pt": "Exportar overlay PNG",
    },
    "project.export_png.saved": {
        "en": "PNG exported: {path}",
        "pt": "PNG exportado: {path}",
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
        "en": "Error loading deformed",
        "pt": "Erro ao carregar deformada",
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
        "en": "The reference and deformed images currently have different visual scales.\n\nCalibration may become inconsistent unless both vehicles are visually matched in size before calibration.\n\nContinue anyway?",
        "pt": "As imagens de referência e deformada estão atualmente com escalas visuais diferentes.\n\nA calibração pode ficar inconsistente se ambos os veículos não estiverem visualmente compatíveis em tamanho antes da calibração.\n\nDeseja continuar mesmo assim?",
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
        "en": "A/B source: -",
        "pt": "Origem de A/B: -",
    },
    "calc.ab_source_nhtsa": {
        "en": "A/B source: NHTSA library | {label}",
        "pt": "Origem de A/B: Biblioteca NHTSA | {label}",
    },
    "calc.ab_source_generic": {
        "en": "A/B source: Generic class | {label}",
        "pt": "Origem de A/B: Classe genérica | {label}",
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
    "calc.ab_tooltip": {
        "en": (
            "Test: {label}\n"
            "Test #: {test_number}\n"
            "Report: {report_number}\n"
            "Impact speed: {impact_speed} km/h\n"
            "Velocity change: {velocity_change} km/h\n"
            "Damage speed: {damage_speed} km/h\n"
            "Basis: {speed_basis}\n"
            "Angle: {angle} deg\n"
            "A: {A}\n"
            "B: {B}"
        ),
        "pt": (
            "Teste: {label}\n"
            "Teste #: {test_number}\n"
            "Relatório: {report_number}\n"
            "Velocidade de impacto: {impact_speed} km/h\n"
            "Variação de velocidade: {velocity_change} km/h\n"
            "Velocidade de danos: {damage_speed} km/h\n"
            "Base: {speed_basis}\n"
            "Ângulo: {angle} graus\n"
            "A: {A}\n"
            "B: {B}"
        ),
    },
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
        "en": "Compute A/B from NHTSA report",
        "pt": "Calcular A/B a partir de relatório NHTSA",
    },
    "calc.ab_source_nhtsa_report": {
        "en": "A/B source: NHTSA report | {label}",
        "pt": "Origem de A/B: Relatório NHTSA | {label}",
    },
    "report.ab_source_reference": {
        "en": "Source document",
        "pt": "Documento de origem",
    },
    "calc.edit_ab_from_nhtsa": {
        "en": "Edit NHTSA A/B inputs",
        "pt": "Editar entradas NHTSA de A/B",
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
        "en": "A/B Source",
        "pt": "Origem dos coeficientes A/B",
    },
    "calc.group.params": {
        "en": "Parameters",
        "pt": "Parâmetros",
    },
    "calc.group.calc": {
        "en": "Calculation",
        "pt": "Cálculo",
    },
    "project.untitled": {
        "en": "untitled",
        "pt": "sem_titulo",
    },
    "calc.ab_menu": {
        "en": "Library / A/B files...",
        "pt": "Biblioteca / Arquivos A/B...",
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
        "en": "A/B source: A/B file | {label}",
        "pt": "Origem de A/B: Arquivo A/B | {label}",
    },
    "report.bumper_offset_m": {
        "en": "Offset to bumper crossmember (m)",
        "pt": "Offset até a travessa do para-choque (m)",
    },
    "label.bumper_offset_m": {
        "en": "Offset to bumper crossmember (m)",
        "pt": "Distância até a travessa do para-choque (m)",
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
    "report.warning.incomplete": {
        "en": "WARNING: Project incomplete — energy or speed not yet calculated.",
        "pt": "ATENÇÃO: Projeto incompleto — energia ou velocidade ainda não calculadas.",
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
