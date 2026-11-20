import hashlib
import json
import os
from pathlib import Path
import struct

import pytest

from echo_game import package_data as decoder


REPORT = Path(__file__).resolve().parents[1] / "docs" / "echo" / "packaged-obstacle-data.json"


def u32(value):
    return struct.pack("<I", value)


def string(value):
    raw = value.encode("ascii")
    return bytes([len(raw)]) + raw


def decl(name="synthetic", annotation="", args=None, returns=()):
    fields = [1, 13 if args is not None else 2] + [0] * 9
    raw = string(name) + string("") + string(annotation) + struct.pack("<11I", *fields)
    if args is not None:
        raw += u32(len(args)) + b"".join(u32(i) for i in args)
        raw += u32(len(returns)) + b"".join(u32(i) for i in returns)
    return raw


def script(top=(), local=(), tail=b""):
    return u32(len(top)) + b"".join(top) + u32(len(local)) + b"".join(local) + tail


def package(members):
    payload = b""
    table = u32(len(members))
    for identifier, raw in members:
        table += struct.pack("<III", identifier, len(payload), len(raw))
        payload += raw
    return table + payload


def test_package_offsets_are_payload_relative_and_ids_opaque():
    data = package([(0xDEADBEEF, b"abc"), (7, b"de")])
    payload_offset, members = decoder.decode_package(data)
    assert payload_offset == 28
    assert members[0].identifier == 0xDEADBEEF
    assert members[1].payload_relative_offset == 3
    assert members[1].absolute_start == 31
    assert members[1].read(data) == b"de"
    assert members[1].identity(data)["sha256"] == hashlib.sha256(b"de").hexdigest()
    assert members[0].identity(data)["table_absolute_end"] == 16


def test_empty_table_and_empty_script():
    assert decoder.decode_package(u32(0)) == (4, [])
    result = decoder.decode_script(script())
    assert result["coverage"]["bytes_decoded"] == 8
    assert result["unknown_tail"]["size"] == 0
    assert result["unknown_tail"]["sha256"] == hashlib.sha256(b"").hexdigest()


@pytest.mark.parametrize("data", [b"", b"\x01", u32(0xFFFFFFFF), u32(1) + b"\x00" * 11,
                                      u32(1) + struct.pack("<III", 1, 1, 0),
                                      u32(1) + struct.pack("<III", 1, 0, 1),
                                      u32(1) + struct.pack("<III", 1, 0xFFFFFFFF, 0xFFFFFFFF)])
def test_invalid_package_counts_and_ranges(data):
    with pytest.raises(decoder.DecodeError):
        decoder.decode_package(data)


def test_full_declarations_include_argument_and_return_extensions_and_offsets():
    top = [decl("f", args=[6, 6], returns=[2, 6]), decl("plain", annotation="0,20: default=5")]
    local = [decl("local")]
    raw = script(top, local, tail=b"\x01\x02opaque")
    result = decoder.decode_script(raw, absolute_start=1000)
    first, second = result["top_declarations"]
    signature = first["function_signature"]
    assert signature["argument_type_ids"] == [6, 6]
    assert signature["return_type_ids"] == [2, 6]
    assert signature["return_count"] == 2
    assert first["byte_range"]["member_start"] == 4
    assert first["byte_range"]["member_end"] == second["byte_range"]["member_start"]
    assert first["byte_range"]["absolute_start"] == 1004
    assert first["raw_fields"] == [1, 13] + [0] * 9
    for i, offset in enumerate(first["raw_field_member_offsets"]):
        assert struct.unpack_from("<I", raw, offset)[0] == first["raw_fields"][i]
        assert first["raw_field_absolute_offsets"][i] == offset + 1000
    assert second["annotation_default"]["default_literal"] == "5"
    assert "not a level-instance" in second["annotation_default"]["scope"]
    assert result["local_declarations"][0]["name"] == "local"
    decoded = len(raw) - len(b"\x01\x02opaque")
    assert result["coverage"]["bytes_decoded"] == decoded
    assert result["unknown_tail"]["absolute_start"] == 1000 + decoded
    assert result["unknown_tail"]["sha256"] == hashlib.sha256(b"\x01\x02opaque").hexdigest()
    assert not result["coverage"]["execution_recovered"]


def test_zero_argument_and_return_counts_still_consume_both_counts():
    result = decoder.decode_script(script([decl("f", args=[])]))
    signature = result["top_declarations"][0]["function_signature"]
    assert signature["argument_count"] == signature["return_count"] == 0
    assert signature["byte_range"]["size"] == 8
    assert result["coverage"]["bytes_undecoded"] == 0


@pytest.mark.parametrize("raw", [b"", b"\x00" * 3, u32(0xFFFFFFFF),
                                     u32(0) + u32(0xFFFFFFFF),
                                     u32(1) + decl()[:-1],
                                     u32(1) + b"\xff" + b"\x00" * 60,
                                     u32(1) + b"\x01\xff\x00\x00" + b"\x00" * 44,
                                     u32(1) + b"\x01\x00\x00\x00" + b"\x00" * 44])
def test_invalid_script_counts_ascii_and_truncation(raw):
    with pytest.raises(decoder.DecodeError):
        decoder.decode_script(raw, absolute_start=100)


def test_function_extension_invalid_argument_count():
    raw = u32(1) + decl("f", args=[])[:-8] + u32(0xFFFFFFFF)
    with pytest.raises(decoder.DecodeError, match="argument type"):
        decoder.decode_script(raw)


def test_function_extension_invalid_return_count():
    raw = u32(1) + decl("f", args=[])[:-4] + u32(0xFFFFFFFF)
    with pytest.raises(decoder.DecodeError, match="return type"):
        decoder.decode_script(raw)


@pytest.mark.parametrize("length", range(8))
def test_function_extension_truncation(length):
    prefix = u32(1) + decl("f", args=[])[:-8]
    with pytest.raises(decoder.DecodeError):
        decoder.decode_script(prefix + b"\x00" * length)


def test_declared_return_values_are_not_misread_as_local_count():
    raw = script([decl("vector", args=[6], returns=[6])], [decl("v")])
    decoded = decoder.decode_script(raw)
    assert decoded["local_count"] == 1
    assert decoded["local_declarations"][0]["name"] == "v"
    assert decoded["coverage"]["bytes_undecoded"] == 0


def test_readable_records_preserve_duplicates_unknown_lines_and_raw_values():
    raw = (b'worldgravity = "0.000002,-10.000000"\r\n\r\n'
           b'boydir = "-1.000000"\nworldgravity = "not a vector"\n'
           b'opaque\xff\nchapter1 = "data/levels/synthetic.branch 3"')
    result = decoder.decode_readable_records(raw, absolute_start=500)
    records = result["records"]
    assert [record["key"] for record in records] == ["worldgravity", "boydir", "worldgravity", "chapter1"]
    assert records[0]["value_literal"] == "0.000002,-10.000000"
    assert records[0]["interpretation"]["value"] == [0.000002, -10.0]
    assert records[0]["interpretation"]["units"] == "unknown"
    assert records[1]["interpretation"]["value"] == -1.0
    assert "interpretation" not in records[2]
    assert records[3]["interpretation"]["branch_entry"] == 3
    assert not records[3]["interpretation"]["resolved"]
    assert result["coverage"]["bytes_undecoded"] == len(b"opaque\xff\n")
    unknown = result["unknown_regions"][0]
    assert unknown["sha256"] == hashlib.sha256(b"opaque\xff\n").hexdigest()
    assert unknown["absolute_start"] == unknown["member_start"] + 500
    assert not result["coverage"]["complete"]
    for record in records:
        bounds = record["value_range"]
        assert raw[bounds["member_start"]:bounds["member_end"]].decode("ascii") == record["value_literal"]


@pytest.mark.parametrize("raw", [b'key = "unterminated', b'key = "escaped\\quote"',
                                     b'key = "\xff"', b'key = "a" extra', b'key = "a"\r'])
def test_unsupported_text_grammar_stays_unknown(raw):
    result = decoder.decode_readable_records(raw)
    assert not result["records"]
    assert result["coverage"]["bytes_undecoded"] == len(raw)
    assert result["unknown_regions"][0]["size"] == len(raw)


@pytest.mark.parametrize("annotation", ["", "signal", "not default=5", "0,20:default=inf", "0,20:default=1e999"])
def test_annotation_defaults_require_supported_finite_syntax(annotation):
    assert decoder.annotation_default(annotation) is None


def test_package_summary_retains_gaps_and_never_assumes_range_contiguity(tmp_path):
    raw = script()
    path = tmp_path / "synthetic.pkg"
    path.write_bytes(u32(1) + struct.pack("<III", 5, 3, len(raw)) + b"gap" + raw + b"end")
    result = decoder.inspect_package(path, {0: "synthetic"}, script=True)
    gaps = result["table"]["gap_regions"]
    assert [gap["size"] for gap in gaps] == [3, 3]
    assert gaps[0]["sha256"] == hashlib.sha256(b"gap").hexdigest()
    assert not result["table"]["last_member_ends_at_eof"]


@pytest.fixture(scope="module")
def saved_report():
    return json.loads(REPORT.read_text(encoding="utf-8"))


def test_saved_report_identities_selection_and_portable_coverage(saved_report):
    assert saved_report["schema_version"] == decoder.SCHEMA_VERSION
    boot, runtime = saved_report["packages"]
    assert boot["sha256"] == "e7b5128c8ea5251959f6af78f418f89ceb188d8dc2145e3a17afb5ecb8ebbf5f"
    assert runtime["sha256"] == "e5cdd74fb89130f7dd3a5e61e949ad9e38f2962c6d03abaa6b5af09babcb14ff"
    assert (boot["table"]["member_count"], boot["table"]["payload_offset"]) == (1641, 19696)
    assert (runtime["table"]["member_count"], runtime["table"]["payload_offset"]) == (455, 5464)
    assert [item["member"]["index"] for item in boot["members"]] == list(decoder.SCRIPT_SELECTION)
    for package in (boot, runtime):
        assert package["table"]["all_ranges_within_file"]
        assert package["table"]["overlap_bytes"] == 0
        assert not package["table"]["gap_regions"]
        coverage = package["coverage"]
        assert coverage["selected_member_bytes"] == coverage["selected_bytes_decoded"] + coverage["selected_bytes_undecoded"]
        assert coverage["table_bytes_decoded"] + coverage["selected_member_bytes"] + coverage["unselected_member_bytes"] == package["size"]
        for item in package["members"]:
            member = item["member"]
            assert len(member["sha256"]) == 64
            assert member["sha256"] == item["sha256"]
            assert int(member["identifier_hex"], 16) == member["identifier"]
            assert member["absolute_start"] == package["table"]["payload_offset"] + member["payload_relative_offset"]
            assert item["coverage"]["member_size"] == member["size"]
            assert not item["coverage"]["execution_recovered"]


def test_saved_script_declarations_account_for_prefix_and_unknown_tail(saved_report):
    boot = saved_report["packages"][0]
    expected = {1518: (19, 11, 1739, 428), 1566: (5, 1, 345, 84),
                1569: (42, 51, 5748, 1394), 1574: (18, 9, 1671, 432),
                1575: (16, 8, 1464, 324), 1620: (13, 18, 1858, 504)}
    for item in boot["members"]:
        assert (item["top_count"], item["local_count"], item["coverage"]["bytes_decoded"], item["unknown_tail"]["size"]) == expected[item["member"]["index"]]
        next_offset = 0
        for scope in ("top", "local"):
            count_range = item[f"{scope}_count_range"]
            assert count_range["member_start"] == next_offset
            next_offset += 4
            assert len(item[f"{scope}_declarations"]) == item[f"{scope}_count"]
            for record in item[f"{scope}_declarations"]:
                bounds = record["byte_range"]
                assert bounds["member_start"] == next_offset
                assert bounds["absolute_start"] == item["member"]["absolute_start"] + next_offset
                assert len(record["raw_fields"]) == 11
                next_offset = bounds["member_end"]
        tail = item["unknown_tail"]
        assert tail["member_start"] == next_offset == item["coverage"]["bytes_decoded"]
        assert tail["absolute_end"] == item["member"]["absolute_end"]
        assert tail["status"] == "undecoded"
        assert len(tail["sha256"]) == 64
    assert boot["coverage"]["selected_bytes_decoded"] == 12825
    assert boot["coverage"]["selected_bytes_undecoded"] == 3166


def test_saved_inferred_return_types_and_annotation_defaults(saved_report):
    observation = saved_report["observations"]
    functions = {item["name"]: item["signature"] for item in observation["nonempty_return_type_extensions"]}
    assert set(functions) == {"DegreeToRadian", "RadianToDegree", "getPerpendicular", "signedAngleBetweenVectors"}
    assert functions["getPerpendicular"]["argument_type_ids"] == [6]
    assert functions["getPerpendicular"]["return_type_ids"] == [6]
    assert functions["signedAngleBetweenVectors"]["argument_type_ids"] == [6, 6]
    assert functions["signedAngleBetweenVectors"]["return_type_ids"] == [2]
    defaults = {(item["member_index"], item["name"]): item for item in observation["annotation_defaults"]}
    assert defaults[1620, "length"]["default_number"] == 4.0
    assert defaults[1620, "numberOfSegments"]["default_number"] == 6.0
    assert defaults[1620, "segmentDensity"]["default_number"] == 0.25
    assert defaults[1574, "areaPerSecond"]["default_number"] == 5.0
    assert defaults[1575, "areaPerSecond"]["default_number"] == 5.0
    assert defaults[1569, "worldStrength"]["default_number"] == 10.0
    assert all("not a level-instance" in item["scope"] for item in defaults.values())


def test_saved_runtime_all_records_and_checkpoint_literals(saved_report):
    runtime = saved_report["packages"][1]
    assert [item["member"]["index"] for item in runtime["members"]] == list(range(103))
    assert runtime["coverage"]["selected_bytes_decoded"] == 20844
    assert runtime["coverage"]["selected_bytes_undecoded"] == 0
    chapters = runtime["members"][0]["records"]
    assert len(chapters) == 39
    assert [r["interpretation"]["chapter_number"] for r in chapters] == list(range(1, 40))
    assert chapters[-1]["value_literal"] == "data/levels/modern_underground/gravity_jump.branch 4"
    for item in runtime["members"][1:]:
        assert item["coverage"]["complete"]
        assert not item["unknown_regions"]
        assert {record["key"] for record in item["records"]} == {"boydir", "boygravity", "boypaused", "boypos", "savepointnode", "worldgravity"}
        assert len(item["records"]) == 6
    counts = saved_report["observations"]["checkpoint_literal_counts"]
    assert counts["boydir"] == {"1.000000": 86, "-1.000000": 16}
    assert counts["boygravity"] == {"0.000000,0.000000": 102}
    assert counts["boypaused"] == {"true": 3, "false": 99}
    assert counts["worldgravity"]["0.000000,-10.000000"] == 94
    assert sum(counts["worldgravity"].values()) == 102
    assert len(saved_report["observations"]["nonstandard_checkpoint_worldgravity"]) == 8


@pytest.mark.skipif(not os.environ.get("LIMBO_REFERENCE_ROOT"), reason="optional caller-selected local reference; portable tests need no proprietary bytes")
def test_optional_local_reference_reproduces_saved_report(saved_report):
    actual = decoder.inspect(Path(os.environ["LIMBO_REFERENCE_ROOT"]))
    for expected, observed in zip(saved_report["packages"], actual["packages"]):
        assert expected["sha256"] == observed["sha256"]
        assert expected["table"] == observed["table"]
        assert expected["members"] == observed["members"]
        assert expected["coverage"] == observed["coverage"]
    assert actual["observations"] == saved_report["observations"]
