import csv
import tempfile
import unittest
from pathlib import Path

from create_fathomnet_csv import convert_dataset_to_csv, load_json_file

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = ROOT / "input"


class FathomNetCsvConversionTests(unittest.TestCase):
    def test_core_json_fields_only(self):
        dataset = load_json_file(EXAMPLES_DIR / "dataset.json")

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "core_output.csv"
            row_count = convert_dataset_to_csv(dataset, output_path)

            self.assertEqual(row_count, 4)

            with output_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(len(rows), 4)
            self.assertEqual(set(rows[0].keys()), {"concept", "image_url", "x", "y", "width", "height"})
            self.assertEqual(rows[0]["concept"], "Acanthaster planci")
            self.assertEqual(rows[0]["image_url"], "")
            self.assertEqual(rows[0]["x"], "12")
            self.assertEqual(rows[0]["y"], "34")
            self.assertEqual(rows[0]["width"], "45")
            self.assertEqual(rows[0]["height"], "67")

    def test_optional_metadata_csvs_are_merged(self):
        dataset = load_json_file(EXAMPLES_DIR / "dataset.json")
        image_metadata_path = EXAMPLES_DIR / "image_metadata.csv"
        object_metadata_path = EXAMPLES_DIR / "object_metadata.csv"

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "optional_output.csv"
            row_count = convert_dataset_to_csv(
                dataset,
                output_path,
                image_metadata_path=image_metadata_path,
                object_metadata_path=object_metadata_path,
            )

            self.assertEqual(row_count, 4)

            with output_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[0]["image_url"], "https://example.com/images/example_001.jpg")
            self.assertEqual(rows[0]["latitude"], "-64.1")
            self.assertEqual(rows[0]["longitude"], "12.3")
            self.assertEqual(rows[0]["timestamp"], "2023-01-01T12:34:56Z")
            self.assertEqual(rows[0]["depth"], "120")
            self.assertEqual(rows[0]["temperature"], "4.5")
            self.assertEqual(rows[0]["groupof"], "true")
            self.assertEqual(rows[0]["occluded"], "false")
            self.assertEqual(rows[0]["userdefinedkey"], "custom-tag-1")
            self.assertEqual(rows[1]["groupof"], "false")
            self.assertEqual(rows[1]["truncated"], "true")
            self.assertEqual(rows[2]["image_url"], "https://example.com/images/example_002.jpg")
            self.assertEqual(rows[2]["imagingtype"], "video")
            self.assertEqual(rows[2]["observer"], "observer_02")
            self.assertEqual(rows[3]["userdefinedkey"], "custom-tag-4")

    def test_output_csv_is_formatted_for_all_supported_fields(self):
        dataset = load_json_file(EXAMPLES_DIR / "dataset.json")
        image_metadata_path = EXAMPLES_DIR / "image_metadata.csv"
        object_metadata_path = EXAMPLES_DIR / "object_metadata.csv"

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "formatted_output.csv"
            convert_dataset_to_csv(
                dataset,
                output_path,
                image_metadata_path=image_metadata_path,
                object_metadata_path=object_metadata_path,
            )

            with output_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                fieldnames = reader.fieldnames
                rows = list(reader)

            expected_fieldnames = [
                "concept",
                "image_url",
                "x",
                "y",
                "width",
                "height",
                "latitude",
                "longitude",
                "timestamp",
                "depth",
                "temperature",
                "imagingtype",
                "observer",
                "oxygen",
                "pressure",
                "salinity",
                "groupof",
                "occluded",
                "truncated",
                "userdefinedkey",
            ]

            self.assertEqual(fieldnames, expected_fieldnames)
            self.assertEqual(len(rows), 4)
            for row in rows:
                self.assertEqual(set(row.keys()), set(expected_fieldnames))
                self.assertTrue(row["concept"])
                self.assertTrue(row["image_url"] in {"", "https://example.com/images/example_001.jpg", "https://example.com/images/example_002.jpg", "https://example.com/images/example_003.jpg"})
                self.assertTrue(row["x"])
                self.assertTrue(row["y"])
                self.assertTrue(row["width"])
                self.assertTrue(row["height"])


if __name__ == "__main__":
    unittest.main()
