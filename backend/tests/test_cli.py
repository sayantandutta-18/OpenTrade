"""Tests for ImpactLab CLI commands."""

from pathlib import Path

from impactlab.cli import main


def test_cli_book_command(capsys) -> None:  # type: ignore[no-untyped-def]
    main(["book", "--profile", "mid", "--seed", "1", "--warmup", "5", "--depth", "5"])
    captured = capsys.readouterr()
    assert "ImpactLab Order Book Ladder: MID_CAP" in captured.out
    assert "SPREAD :" in captured.out
    assert "BID" in captured.out
    assert "ASK" in captured.out


def test_cli_impact_command(capsys) -> None:  # type: ignore[no-untyped-def]
    main(
        [
            "impact",
            "--profile",
            "small",
            "--side",
            "buy",
            "--qty",
            "200",
            "--seed",
            "1",
            "--warmup",
            "5",
        ]
    )
    captured = capsys.readouterr()
    assert "ImpactLab Market Impact Analysis" in captured.out
    assert "Slippage vs Best" in captured.out
    assert "Statutory & Broker Charges" in captured.out


def test_cli_sweep_command(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    csv_file = tmp_path / "sweep.csv"
    main(
        [
            "sweep",
            "--profile",
            "mid",
            "--sizes",
            "50,100,200",
            "--seed",
            "1",
            "--warmup",
            "5",
            "--csv",
            str(csv_file),
        ]
    )
    captured = capsys.readouterr()
    assert "ImpactLab Size Sweep: MID_CAP" in captured.out
    assert csv_file.exists()
    content = csv_file.read_text(encoding="utf-8")
    assert "profile,side,size,filled_qty" in content
    assert "mid_cap,BUY,50" in content
