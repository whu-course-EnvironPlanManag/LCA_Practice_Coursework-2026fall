from pathlib import Path

import schemdraw
import schemdraw.flow as flow
from schemdraw import elements as elm


OUTPUT_DIR = Path(__file__).resolve().parent


def build_diagram() -> schemdraw.Drawing:
    drawing = schemdraw.Drawing(show=False)
    drawing.config(font="sans-serif", fontsize=9, color="#263238", lw=1.2)

    feed = drawing.add(
        flow.Data(w=3.8, h=1.0, fill="#dceef2")
        .at((0, 0))
        .label("Baled PET bottles\n1,000 kg", fontsize=10)
    )
    debaling = drawing.add(
        flow.Process(w=4.2, h=1.25, fill="#e8f1ec")
        .at((0, -2))
        .label("1  Debaling and dry screening")
    )
    washing = drawing.add(
        flow.Process(w=4.2, h=1.25, fill="#e8f1ec")
        .at((0, -4))
        .label("2  Wet grinding and hot alkaline wash")
    )
    separation = drawing.add(
        flow.Process(w=4.2, h=1.25, fill="#e8f1ec")
        .at((0, -6))
        .label("3  Sink-float separation")
    )
    sorting = drawing.add(
        flow.Process(w=4.2, h=1.25, fill="#e8f1ec")
        .at((0, -8))
        .label("4  Optical sorting, dewatering and drying")
    )
    extrusion = drawing.add(
        flow.Process(w=4.2, h=1.25, fill="#e8f1ec")
        .at((0, -10))
        .label("5  Vacuum extrusion and SSP")
    )
    product = drawing.add(
        flow.Data(w=3.8, h=1.0, fill="#dceef2")
        .at((0, -12))
        .label("Bottle-grade rPET\n800 kg", fontsize=10)
    )

    waste_streams = [
        (debaling, (-6.5, -2), "Labels + dirt\n45 kg"),
        (washing, (-6.5, -4), "Wash residues\n35 kg"),
        (separation, (-6.5, -6), "HDPE carryover loss\n5 kg"),
        (sorting, (-6.5, -8), "Off-spec flakes + fines\n40 kg"),
    ]
    for source, position, label in waste_streams:
        stream = drawing.add(
            flow.Data(w=3.6, h=1.0, fill="#f5e8df")
            .at(position)
            .label(label, fontsize=9)
        )
        drawing.add(elm.Line(arrow="->").at(source.W).to(stream.E))

    hdpe = drawing.add(
        flow.Data(w=3.6, h=1.0, fill="#f4edcf")
        .at((6.5, -6))
        .label("Recovered HDPE\n75 kg", fontsize=9)
    )
    drawing.add(elm.Line(arrow="->").at(separation.E).to(hdpe.W))

    main_path = [feed, debaling, washing, separation, sorting, extrusion, product]
    for source, target in zip(main_path, main_path[1:]):
        drawing.add(elm.Line(arrow="->").at(source.S).to(target.N))

    return drawing


def main() -> None:
    drawing = build_diagram()
    drawing.draw(show=False, backend="svg")
    drawing.save(OUTPUT_DIR / "process_flow_diagram.svg")


if __name__ == "__main__":
    main()