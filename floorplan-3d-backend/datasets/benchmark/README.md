# Benchmark Regression Dataset

This directory contains floor plan images and their corresponding ground truth files for parser regression testing.

## Structure

```
datasets/
  benchmark/
    README.md                   ← this file
    apartment_01.png            ← test image
    apartment_01_gt.json        ← ground truth for apartment_01.png
    villa_01.png
    villa_01_gt.json
    office_01.png
    office_01_gt.json
    irregular_01.png
    irregular_01_gt.json
    multi_room_01.png
    multi_room_01_gt.json
```

## Ground Truth Schema

Each `*_gt.json` file must conform to this schema (all coordinates in **metres**):

```json
{
  "walls": [
    { "start": [0.0, 0.0], "end": [5.0, 0.0] },
    { "start": [5.0, 0.0], "end": [5.0, 4.0] }
  ],
  "rooms": [
    {
      "polygon": [[0.0, 0.0], [5.0, 0.0], [5.0, 4.0], [0.0, 4.0]],
      "type": "Bedroom"
    }
  ],
  "doors": [
    { "center": [2.5, 0.0], "width": 0.9 }
  ],
  "windows": [
    { "center": [1.0, 4.0], "width": 1.2 }
  ]
}
```

## Adding a New Test Case

1. Place the floor plan image (PNG or JPG) here.
2. Create a sidecar `*_gt.json` with the expected output.
3. Run `python benchmark.py` — it will automatically discover the new image.

## Regression Policy

Parser changes that reduce **wall IoU** below 0.70 or **room IoU** below 0.65
are considered regressions and must be justified before merging.
