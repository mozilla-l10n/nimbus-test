#!/usr/bin/env python3

# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from collections import defaultdict
from configparser import ConfigParser
from pathlib import Path
import argparse
import json
import os
import sys

try:
    from compare_locales import paths
    from compare_locales import parser
except ImportError as e:
    print("FATAL: make sure that dependencies are installed")
    print(e)
    sys.exit(1)


class StringExtraction:
    def __init__(self, l10n_path, reference_locale):
        """Initialize object."""

        self.translations = defaultdict(dict)

        self.l10n_path = l10n_path
        self.reference_locale = reference_locale

    def extractStrings(self):
        """Extract strings from TOML file."""

        basedir = os.path.dirname(self.l10n_path)
        project_config = paths.TOMLParser().parse(self.l10n_path, env={"l10n_base": ""})
        basedir = os.path.join(basedir, project_config.root)

        reference_cache = {}

        if not project_config.all_locales:
            print("No locales defined in the project configuration.")

        for locale in project_config.all_locales:
            print(f"Extracting strings for locale: {locale}.")
            files = paths.ProjectFiles(locale, [project_config])
            for l10n_file, reference_file, _, _ in files:
                if not os.path.exists(l10n_file):
                    # File not available in localization
                    continue

                if not os.path.exists(reference_file):
                    # File not available in reference
                    continue

                key_path = os.path.relpath(reference_file, basedir)
                experiment_id = os.path.basename(os.path.splitext(key_path)[0])
                try:
                    p = parser.getParser(reference_file)
                except UserWarning:
                    continue
                if key_path not in reference_cache:
                    p.readFile(reference_file)
                    reference_cache[key_path] = set(p.parse().keys())
                    self.translations[self.reference_locale].update(
                        (
                            f"{experiment_id}:{entity.key}",
                            entity.raw_val,
                        )
                        for entity in p.parse()
                    )

                p.readFile(l10n_file)
                self.translations[locale].update(
                    (
                        f"{experiment_id}:{entity.key}",
                        entity.raw_val,
                    )
                    for entity in p.parse()
                )

            # Remove obsolete strings not available in the reference locale
            if locale != self.reference_locale:
                self.translations[locale] = {
                    k: v
                    for (k, v) in self.translations[locale].items()
                    if k in self.translations[self.reference_locale]
                }
            print(f"  {len(self.translations[locale])} strings extracted")

    def getTranslations(self):
        """Return translations and stats"""

        json_output = {}
        for locale, messages in self.translations.items():
            for full_id, translation in messages.items():
                experiment_id, message_id = full_id.split(":")
                if experiment_id not in json_output:
                    json_output[experiment_id] = {
                        "translations": defaultdict(dict),
                        "complete_locales": [],
                    }
                json_output[experiment_id]["translations"][locale][
                    message_id
                ] = translation

        # Identify complete locales for each experiment, and remove
        # translations for partially translated locales.
        partial_experiments = []
        for exp_id, exp_data in json_output.items():
            locales = list(exp_data["translations"].keys())
            locales.sort()
            reference_ids = list(exp_data["translations"][self.reference_locale].keys())

            incomplete_locales = []
            for l in locales:
                l10n_ids = list(exp_data["translations"][l].keys())
                if len(set(reference_ids) - set(l10n_ids)) == 0:
                    exp_data["complete_locales"].append(l)
                else:
                    incomplete_locales.append(l)
            exp_data["complete_locales"].sort()

            # Remove partially translated locales
            for l in incomplete_locales:
                del exp_data["translations"][l]

            if (list(set(locales) - set(incomplete_locales))) == [
                self.reference_locale
            ]:
                partial_experiments.append(exp_id)

        # Remove experiments without complete translations
        for exp_id in partial_experiments:
            del json_output[exp_id]

        return json_output


def main():
    # Read command line input parameters
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--toml", dest="toml_path", help="Path to l10n.toml file", required="True"
    )
    parser.add_argument(
        "--ref", dest="reference_code", help="Reference language code", default="en-US"
    )
    parser.add_argument(
        "--dest", dest="dest_path", help="Path used to output files", required="True"
    )
    args = parser.parse_args()

    extracted_strings = StringExtraction(
        l10n_path=args.toml_path,
        reference_locale=args.reference_code,
    )
    extracted_strings.extractStrings()
    translations = extracted_strings.getTranslations()

    for exp_id, exp_data in translations.items():
        filename = os.path.join(args.dest_path, f"{exp_id}.json")
        with open(filename, "w", encoding="utf8") as f:
            json.dump(exp_data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
