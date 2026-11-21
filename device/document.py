"""Build the Ress Vocal device document from the panel specification."""
from __future__ import annotations

import hashlib

from devices.common.document_graph import iter_owned_objects
from devices.common.panel_helpers import connection, grid_layout as _grid_layout, obj, value as v


def grid_layout(x, y, w, h):
    """The mockup is drawn in fractions of a grid unit; the document stores i16."""
    return _grid_layout(int(round(x)), int(round(y)), int(round(w)), int(round(h)))

import bwui.emit as bwui_emit
from panel_spec import PANEL
from spec import INDEXED, MODELS, PANEL_HEIGHT, PANEL_WIDTH, PARAMS, TOGGLES

KNOB_SIZE_MAIN = 1
KNOB_SIZE_SMALL = 1


def owned(*objects):
    return [{"Object": item} for item in objects]


def settings(connections=()):
    desktop = obj(17, "desktop_settings", {
        "x#17": v("Int16", 0), "y#18": v("Int16", 0),
        "color#19": v("Color", [0.5, 0.5, 0.5, 1.0]),
    })
    return v("Object", obj(236, "component_settings", {
        "desktop_settings#612": v("Object", desktop),
        "inport_connections#614": v("ObjectList", list(connections)),
        "is_polyphonic#615": v("Bool", False),
    }))


def proxy(*, output=False, note=False):
    caption = " Note out" if note else " Audio in (PARENT)" if output else " Audio out (PARENT)"
    port_fields = {
        "name#498": v("String", ""), "description#4741": v("String", ""),
        "decorated_name#499": v("String", caption), "is_inport#500": v("Bool", output),
        "is_optional#1384": v("Bool", False), "exclude_from_graph#7174": v("Bool", False),
    }
    if note:
        port_fields["oversampling#13326"] = v("Byte", 0)
        port = obj(61, "note_port", port_fields)
    else:
        port_fields.update({"channel_count#372": v("Byte", 3), "oversampling#13324": v("Int32", 0)})
        port = obj(242, "audio_port", port_fields)
    return obj(50 if output else 154, "proxy_out_port_component" if output else "proxy_in_port_component", {
        "settings#6194": settings(), "port#301": v("Object", port),
    })


def decimal_atom(key, title, preset, minimum, maximum, default, unit):
    value_type = obj(123, "decimal_value_type", {
        "min#292": v("Double", minimum), "max#293": v("Double", maximum),
        "default_value#891": v("Double", default), "domain#294": v("Byte", 0),
        "engine_domain#295": v("Byte", 0), "value_origin#3014": v("Byte", 0),
        "pixel_step_size#1988": v("Double", -1.0), "unit#296": v("Byte", unit),
        "#297": v("Byte", 2), "parameter_smoothing#4433": v("Bool", True),
        "allow_automation_curves#4434": v("Bool", True),
    })
    return obj(289, "decimal_value_atom", {
        "settings#6194": settings(), "channel_count#607": v("Byte", 0),
        "oversampling#608": v("Byte", 0), "name#374": v("String", title),
        "short_name#821": v("String", title), "preset_identifier#701": v("String", preset),
        "modulations_to_ignore#3826": v("String", ""),
        "value_type#702": v("Object", value_type), "value#712": v("Double", default),
        "allow_automation#7489": v("Bool", True), "allow_modulation#7490": v("Bool", True),
    })


def boolean_atom(title, preset, default):
    value_type = obj(198, "boolean_value_type", {
        "icon_name#4755": v("String", ""), "default_value#6957": v("Bool", default),
    })
    return obj(87, "boolean_value_atom", {
        "settings#6194": settings(), "channel_count#607": v("Byte", 0),
        "oversampling#608": v("Byte", 0), "preset_identifier#701": v("String", preset),
        "name#374": v("String", title), "short_name#821": v("String", ""),
        "modulations_to_ignore#3826": v("String", ""),
        "value_type#702": v("Object", value_type), "value#210": v("Bool", default),
        "allow_automation#7489": v("Bool", True), "allow_modulation#7490": v("Bool", False),
    })


def nitro_port(name, index, channels, *, output, kind=1):
    return obj(2428, "nitro_port_info", {
        "name#8557": v("String", name), "desc#8558": v("String", ""),
        "channel_count#8559": v("Byte", channels), "index#8560": v("Byte", index),
        "kind#8561": v("Byte", kind), "is_input#8562": v("Bool", not output),
        "is_double_precision#10071": v("Bool", False), "is_compressed_mask#8563": v("Int32", 16777215),
        "is_compressable#8564": v("Bool", False), "event_size#8565": v("Byte", 0),
        "event_type#8566": v("String", ""),
    })



def indexed_atom(key, title, preset, names, default=0):
    """A stepped parameter: an index into named items (Bitwig's own choosers use this)."""
    items = [obj(258, "indexed_value_item", {
        "id#650": v("Byte", i), "name#651": v("String", n), "icon#9823": v("String", ""),
    }) for i, n in enumerate(names)]
    value_type = obj(155, "indexed_value_type", {
        "items#393": v("ObjectList", owned(*items)),
        "default_value#6958": v("Int32", default),
        "is_periodic#16667": v("Bool", False),
    })
    return obj(180, "indexed_value_atom", {
        "settings#6194": settings(), "channel_count#607": v("Byte", 0),
        "oversampling#608": v("Byte", 0), "name#374": v("String", title),
        "short_name#821": v("String", title), "preset_identifier#701": v("String", preset),
        "should_inherit_name#10561": v("Bool", False),
        "modulations_to_ignore#3826": v("String", ""),
        "value_type#702": v("Object", value_type),
        "allow_automation#7489": v("Bool", True), "allow_modulation#7490": v("Bool", False),
        "value#457": v("Int32", default),
    })


def button_group(model, x, y, w, h, tooltip="", wrap=2):
    return obj(1712, "button_group_chooser_panel_item", {
        "layout_settings#6226": v("Object", grid_layout(x, y, w, h)),
        "is_visible#6309": v("Bool", True), "is_enabled#6310": v("Bool", True),
        "tooltip_text#6867": v("String", tooltip),
        "help_id#10543": v("String", ""), "help_location#10546": v("Byte", 0),
        "data_model#6220": model, "attribute_id#11012": v("Int16", 457),
        "is_horizontal#6255": v("Bool", True), "break_count#6256": v("Int16", wrap),
        "label_style#6257": v("Byte", 0), "button_style#7548": v("Byte", 0),
        "color#10143": v("Int16", 0),
    })


def chooser(model, x, y, w, h):
    return obj(1714, "popup_chooser_panel_item", {
        "layout_settings#6226": v("Object", grid_layout(x, y, w, h)),
        "is_visible#6309": v("Bool", True), "is_enabled#6310": v("Bool", True),
        "tooltip_text#6867": v("String", ""),
        "data_model#6220": model, "attribute_id#11012": v("Int16", 457),
        "label_style#6262": v("Byte", 0), "style#6266": v("Byte", 7),
        "color#7528": v("Int16", 6),
    })


def knob(model, x, y, w, h, title, size, tooltip=""):
    return obj(1687, "knob_panel_item", {
        "layout_settings#6226": v("Object", grid_layout(x, y, w, h)),
        "is_visible#6309": v("Bool", True), "is_enabled#6310": v("Bool", True),
        "tooltip_text#6867": v("String", tooltip),
        "data_model#6220": model, "title#6241": v("String", title),
        "knob_size#6223": v("Byte", size), "show_value_popup#10569": v("Bool", True),
        "attribute_id#11012": v("Int16", 712), "knob_style#7055": v("Byte", 3),
        "label_color#7056": v("Int16", 6), "pie_color#7057": v("Byte", 6),
    })


def number_field(model, x, y, w, h):
    return obj(1713, "number_field_panel_item", {
        "layout_settings#6226": v("Object", grid_layout(x, y, w, h)),
        "is_visible#6309": v("Bool", True), "is_enabled#6310": v("Bool", False),
        "tooltip_text#6867": v("String", ""),
        "data_model#6220": model, "style#6540": v("Byte", 1),
        "show_value_bar#6581": v("Bool", False), "color#7526": v("Int16", 6),
        "text_alignment#10029": v("Byte", 1), "value_text#10034": v("String", ""),
    })


def toggle(model, x, y, w, h, title):
    return obj(1702, "toggle_button_panel_item", {
        "layout_settings#6226": v("Object", grid_layout(x, y, w, h)),
        "is_visible#6309": v("Bool", True), "is_enabled#6310": v("Bool", True),
        "tooltip_text#6867": v("String", ""),
        "data_model#6220": model, "title#6241": v("String", title),
        "icon_name#6239": v("String", ""), "style#6240": v("Int32", 3),
        "label_style#6267": v("Int32", 0), "invert_value#6552": v("Bool", False),
        "is_selected#6719": v("Bool", False), "color#7527": v("Int32", 999),
        "font#7530": v("Int32", 0),
    })


def label(text, x, y, w, h, align=1):
    return obj(1683, "label_panel_item", {
        "layout_settings#6226": v("Object", grid_layout(x, y, w, h)),
        "text#6219": v("String", text), "color#6520": v("Int16", 6),
        "horizontal_alignment#6400": v("Byte", align), "vertical_alignment#6401": v("Byte", 1),
    })


def main_panel(items):
    grid = obj(1681, "grid_panel_item", {
        "layout_settings#6226": v("NullObject"), "items#6221": v("ObjectList", owned(*items)),
        "border_style#6228": v("Byte", 0), "title#6242": v("String", ""),
        "show_title#6243": v("Bool", False), "title_color#6522": v("Byte", 6),
        "brightness#6245": v("Byte", 0),
    })
    return obj(1680, "panel", {
        "name#6211": v("String", "Main"), "root_item#6212": v("Object", grid),
        "width#6232": v("Int16", PANEL_WIDTH), "height#6233": v("Byte", PANEL_HEIGHT),
        "expressions#6277": v("ObjectList", []),
    })


def metadata(project, revision):
    identity = project["identity"]
    fields = {
        "application_version_name": v("String", project["target"]["bitwigVersion"]),
        "creator": v("String", identity["creator"]), "device_creator": v("String", identity["creator"]),
        "device_category": v("String", identity["category"]),
        "device_description": v("String", project["presentation"]["description"]),
        "device_id": v("String", identity["uuid"]), "device_uuid": v("Uuid", identity["uuid"]),
        "device_name": v("String", project["name"]), "device_type": v("String", "audio_to_audio"),
        "has_audio_input": v("Bool", True), "has_audio_output": v("Bool", True),
        "has_note_input": v("Bool", False), "has_note_output": v("Bool", False),
        "preset_name": v("String", project["name"]), "revision_id": v("String", revision),
        "revision_no": v("Int32", 1), "suggest_for_audio_input": v("Bool", True),
        "suggest_for_note_input": v("Bool", False), "tags": v("String", project["presentation"]["tags"]),
        "type": v("String", "application/bitwig-device"),
    }
    return {**obj(4, "meta", fields), "wide_names": [False] * len(fields)}


def document(project, binary, shader):
    bindings = []

    def ref(target, *, list_entry=False):
        key = "ObjectRef" if list_entry else "value"
        wrapper = {"ObjectRef": 0} if list_entry else v("ObjectRef", 0)
        bindings.append((wrapper, key, target))
        return wrapper

    def wire(target, port=0):
        entry = connection(port=port)
        entry["Object"]["fields"]["source_component#248"] = ref(target)
        return entry

    input_proxy = proxy()
    input_owner = connection()
    input_owner["Object"]["fields"]["source_component#248"] = v("Object", input_proxy)
    audio_source = obj(2000, "audio_source_atom", {
        "settings#6194": settings([input_owner]), "channel_count#607": v("Byte", 0),
        "oversampling#608": v("Byte", 0), "port_color#10378": v("Int16", 999),
        "name#3639": v("String", "In"), "preset_identifier#3640": v("String", "IN"),
    })
    compensation = obj(1371, "delay_compensation_atom", {
        "settings#6194": settings([wire(input_proxy)]), "channel_count#607": v("Byte", 0),
        "oversampling#608": v("Byte", 0),
    })

    params = {}
    param_atoms = []
    for key, title, preset, minimum, maximum, default, unit in PARAMS:
        if key in INDEXED:
            if key == "gate_on":
                start = len(INDEXED[key]) - 1
            elif key == "mode":
                start = 0
            else:
                start = int(default) - 1
            atom = indexed_atom(key, title, preset, INDEXED[key], start)
        else:
            atom = decimal_atom(key, title, preset, minimum, maximum, default, unit)
        params[key] = atom
        param_atoms.append(atom)
    gate_atom = indexed_atom("gate_on", "Gate", "GATE_ON", INDEXED["gate_on"], 1)
    params["gate_on"] = gate_atom
    param_atoms.append(gate_atom)

    toggles = {}
    toggle_atoms = []
    for key, title, preset, default in TOGGLES:
        atom = boolean_atom(title, preset, default)
        toggles[key] = atom
        toggle_atoms.append(atom)

    # Input order follows the Nitro port declarations exactly.
    port_inputs = [nitro_port("in", 0, 2, output=False)]
    connections = [wire(compensation)]
    index = 1
    for key, *_rest in PARAMS:
        kind = 3 if key in INDEXED else 1
        port_inputs.append(nitro_port("p_" + key, index, 1, output=False, kind=kind))
        connections.append(wire(params[key]))
        index += 1
    port_inputs.append(nitro_port("gate_on", index, 1, output=False, kind=3))
    connections.append(wire(gate_atom))
    index += 1
    for key, *_rest in TOGGLES:
        port_inputs.append(nitro_port(key, index, 1, output=False, kind=3))
        connections.append(wire(toggles[key]))
        index += 1

    dsp = obj(1721, "nitro_atom", {
        "settings#6194": settings(connections),
        "channel_count#607": v("Byte", 0), "oversampling#608": v("Byte", 0),
        "fft_order#6567": v("Byte", 0), "code_storage#10421": v("ByteArray", [0, *binary]),
        "is_code_storage_binary_ast#14616": v("Bool", True),
        "use_code_path#11360": v("Bool", False), "code_path#11357": v("String", ""),
        "nitro_inputs#15756": v("ObjectList", owned(*port_inputs)),
        "nitro_outputs#15757": v("ObjectList", owned(
            nitro_port("out", 0, 2, output=True),
            nitro_port("display", 1, 4, output=True),
        )),
    })

    drawing = obj(5512, "", {
        "settings#6194": settings([wire(dsp, 1), *(connection() for _ in range(8))]),
        "channel_count#607": v("Byte", 0), "name#374": v("String", ""),
        "prevent_parent_from_sleeping#11002": v("Bool", False),
        "preset_identifier#701": v("String", "PANEL_DRAWING"), "#16316": v("WideString", shader),
    })

    # The face of the device is described once, in panel_spec.py; this binds its
    # widgets to the atoms built above.
    items = bwui_emit.items(PANEL, lambda key: ref(params[key]),
                            display=lambda: ref(drawing))
    output_proxy = proxy(output=True)
    output_proxy["fields"]["settings#6194"] = settings([wire(dsp, 0)])
    panel = main_panel(items)

    identity = project["identity"]
    body = obj(151, "device_contents", {
        "child_components#173": v("ObjectList", owned(
            audio_source, compensation, *param_atoms, *toggle_atoms, dsp, drawing,
        )),
        "panels#6213": v("ObjectList", owned(panel)),
        "proxy_in_ports#177": v("ObjectList", [ref(input_proxy, list_entry=True), *owned(proxy(note=True))]),
        "proxy_out_ports#178": v("ObjectList", owned(output_proxy)),
        "device_UUID#385": v("Uuid", identity["uuid"]), "device_name#386": v("String", project["name"]),
        "description#2057": v("String", project["presentation"]["description"]),
        "creator#387": v("String", identity["creator"]), "category#390": v("String", identity["category"]),
        "suggest_for_note_input#4846": v("Bool", False), "suggest_for_audio_input#4847": v("Bool", True),
        "settings#6194": v("NullObject"), "fft_order#6566": v("Byte", 0),
        "analysis_fft_order#11047": v("Byte", 11), "analysis_fft_fall_speed#11110": v("Byte", 1),
        "device_revision#13647": v("Byte", 1), "sleep_level_threshold#1977": v("Double", -96.0),
        "sleep_level_timeout#1978": v("Double", 0.05), "prevent_sleep#14608": v("Bool", False),
        "comment#388": v("String", ""), "keywords#389": v("String", project["presentation"]["tags"]),
        "device_type#391": v("Byte", 0), "has_been_modified#392": v("Bool", True),
        "color_tint#13354": v("Color", [0.0, 0.0, 0.0, 0.0]),
    })
    object_ids = {id(item): index for index, item in enumerate(iter_owned_objects(body), 1)}
    for wrapper, key, target in bindings:
        wrapper[key] = object_ids[id(target)]

    revision = hashlib.sha1(f"{identity['uuid']}/v1".encode("utf-8")).hexdigest()
    return {
        "header": {"format_version": 3, "serialization_format": 2, "document_version": 207,
                   "object_offset": 0, "resources_offset": 0, "flags": 0},
        "metadata": metadata(project, revision), "body": body,
        "meta_nonce": "0" * 32, "body_nonce": "0" * 32,
    }



PARAMS_BY_KEY = {p[0]: p for p in PARAMS}
TOGGLES_BY_KEY = {t[0]: t for t in TOGGLES}
