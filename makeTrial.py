from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from pathlib import Path
from typing import List, Union
from copy import deepcopy


class MakeTrial:
    def __init__(
        self,
        font: TTFont,
        keep_g_names: List[int],
        replacer: str,
        path_out: Path,
        suffix: str = "Trial",
        family_name = None,
        ttf_components: bool = True,

    ) -> None:
        self.font = font
        self.keep_g_names = keep_g_names
        self.replacer = replacer
        self.path_out = path_out
        self.suffix = suffix
        self.ttf_components = ttf_components
        self.family_name = family_name

    def process(self) -> None:
        if self.font.has_key("CFF "):
            self.process_cff()
        if self.font.has_key("CFF2"):
            self.process_cff2()
        if self.font.has_key("gvar"):
            self.process_gvar()
        if self.font.has_key("glyf"):
            self.process_glyf()
        if self.font.has_key("hmtx"):
            self.process_hmtx()
        # if self.font.has_key("GPOS"):
        # needs to be implemented
        #     self.process_gpos()
        if self.suffix:
            self.process_name()
        return None

    def process_name(self) -> None:
        
        if not self.family_name:
            family_name = font["name"]
            names = filter(lambda x:x.nameID == 1, font["name"].names)
            names = [i.toUnicode() for i in names]
            name = names[0]
        
        else:
            name = self.family_name

        for name_entry in font["name"].names:
            print(
                name_entry.nameID,
                name_entry.platformID,
                name_entry.platEncID,
                name_entry.toUnicode(),
            )
        return None

    def process_cff(self) -> None:
        cff = self.font["CFF "]
        cmap_reversed = {v: k for k, v in self.font.getBestCmap().items()}
        if hasattr(cff, "desubroutinize"):
            cff.desubroutinize()

        content = cff.cff[cff.cff.keys()[0]]  # can it have more fonts?

        for key in content.CharStrings.keys():
            if key in self.keep_g_names:
                continue
            content.CharStrings[key] = content.CharStrings[self.replacer]
        return None

    def process_cff2(self) -> None:
        cff2 = self.font["CFF2"]

        cmap_reversed = {v: k for k, v in self.font.getBestCmap().items()}
        if hasattr(cff2, "desubroutinize"):
            cff2.desubroutinize()

        content = cff2.cff[cff2.cff.keys()[0]]  # can it have more fonts?

        for key in content.CharStrings.keys():
            if key in self.keep_g_names:
                continue
            content.CharStrings[key] = content.CharStrings[self.replacer]
        return None

    def _process_base(self, table) -> None:
        for glyph_name in self.font.glyphOrder:
            if glyph_name in self.keep_g_names:
                continue
            table[glyph_name] = table[self.replacer]
        return None

    def _kerning_lookup_indexes(self) -> Union[None, list]:
        for feat in self.font["GPOS"].table.FeatureList.FeatureRecord:
            if feat.FeatureTag == "kern":
                return feat.Feature.LookupListIndex
        return None

    def process_gpos(self) -> None:
        lookup_indexes = self._kerning_lookup_indexes()
        if not lookup_indexes:
            return None
        for lookup_index in lookup_indexes:
            lookup = self.font["GPOS"].table.LookupList.Lookup[lookup_index]

            for sub_table in lookup.SubTable:
                if sub_table.Format != 1:
                    continue

                first_glyphs = {
                    idx: g for idx, g in enumerate(sub_table.Coverage.glyphs)
                }
                for idx, pairset in enumerate(sub_table.PairSet):
                    first_glyph = first_glyphs[idx]

                    records = deepcopy(pairset.PairValueRecord)
                    for record in records:
                        if (
                            first_glyph not in self.keep_g_names
                            or record.SecondGlyph not in self.keep_g_names
                        ):
                            pairset.remove(record)

    def process_hmtx(self) -> None:
        self._process_base(self.font["hmtx"])
        return None

    def process_glyf(self) -> None:
        if self.ttf_components:
            glyf = self.font["glyf"]
            gs = self.font.getGlyphSet()
            for glyph_name in self.font.glyphOrder:
                if glyph_name in self.keep_g_names:
                    continue
                pen = TTGlyphPen(gs)
                pen.addComponent(self.replacer, (1, 0, 0, 1, 0, 0))
                glyf[glyph_name] = pen.glyph()
        else:
            self._process_base(self.font["glyf"])
        return None

    def process_gvar(self) -> None:
        self._process_base(self.font["gvar"].variations)
        return None

    def save(self) -> None:
        self.font.save(str(self.path_out))
        return None



if __name__ == "__main__":

    import argparse

    class Formatter(
            argparse.MetavarTypeHelpFormatter,
            argparse.RawDescriptionHelpFormatter
        ):
        pass

    class CustomError(Exception):
        pass

    parser = argparse.ArgumentParser(
        description="Tool for producing trial fonts.",
        formatter_class=Formatter,
        epilog = \
'''
Example command:

python trailer.py font_in.otf font_out.otf --replacer-character n --keep-characters a b c --keep-unicodes-base10 100 101 

The command above font_in.otf as input and outputs font_out.otf. 
It replaces every glyph except those representing characters "a", "b" and "c" & 
glyphs with unicodes 100 & 101 by character "n".
'''
    )
    print(dir(argparse))
    parser.add_argument(
        "font_in", type=Path, help="Path to a font that you want to make trial of."
    )
    parser.add_argument(
        "path_out", type=Path, help="Path where save the trial font to."
    )

    keep_group = parser.add_mutually_exclusive_group(required=True)
    keep_group.add_argument(
        "--keep-characters",
        type=str,
        nargs="+",
        help='Space seperated list of characters f.e. "a b 1 2 3"',
    )
    keep_group.add_argument(
        "--keep-glyph-names",
        type=str,
        nargs="+",
        help='Space seperated list of glyph names f.e. "a b one two three"',
    )
    keep_group.add_argument(
        "--keep-unicodes-base10",
        type=int,
        nargs="+",
        help='Space seperated list of base 10 unicodes to keep f.e. "97 98 49 50 51"',
    )

    replacer_group = parser.add_mutually_exclusive_group(required=True)
    replacer_group.add_argument(
        "--replacer-character",
        type=str,
        help="A character which represents a glyph that will replace glyphs that are not set to be kept",
    )
    replacer_group.add_argument(
        "--replacer-glyph-name",
        type=str,
        help="A glyphname which represents a glyph that will replace glyphs that are not set to be kept",
    )
    replacer_group.add_argument(
        "--replacer-unicode-base10",
        type=int,
        help="A base 10 unicode value of a glyph that will repalce glyphs that are not set to be kept",
    )

    parser.add_argument(
        "--skip",
        type=int,
        default=True,
        help="Stops with an error if glyph that is set to be kept in the font is missing",
    )
    parser.add_argument(
        "--ttf-components",
        type=int,
        default=True,
        help="Add replacer glyph as a component in TT flavoured fonts",
    )

    parser.add_argument(
        "--family-name",
        type=str,
        help="Set font's family name. If not set, the program determines the family name itself. The renaming process is based on this value.",
    )

    args = parser.parse_args()

    replacers = (
        (args.replacer_character, lambda x: cmap.get(ord(x))),
        (args.replacer_glyph_name, lambda x: x),
        (args.replacer_unicode_base10, lambda x: cmap.get(x)),
    )

    font = TTFont(str(args.font_in))
    cmap = font.getBestCmap()
    cmap_reversed = {v: k for k, v in cmap.items()}

    replacer = None
    replacer_glyph_name = None

    for possible_replacer, get_replacer_name in replacers:
        if replacer and possible_replacer:
            print("error")
        if possible_replacer:
            replacer = get_replacer_name(possible_replacer)

    assert replacer in cmap_reversed, "replacer not in font"

    keep_unicodes = []

    if args.keep_unicodes_base10:
        for unicode_entry in args.keep_unicodes_base10:
            keep_unicodes.append(unicode_entry)

    if args.keep_characters:
        for unicode_entry in map(ord, args.keep_characters):
            keep_unicodes.append(unicode_entry)

    keep_g_names = [replacer]

    for unicode_entry in keep_unicodes:
        g_name = cmap.get(unicode_entry)
        if g_name:
            keep_g_names.append(g_name)
        else:
            if not args.skip:
                print("error missing")

    if args.keep_glyph_names:
        for g_name in args.keep_glyph_names:
            if g_name in cmap_reversed:
                keep_g_names.append(g_name)
            else:
                if not args.skip:
                    print("error missing")

    trial = MakeTrial(
        font=font,
        keep_g_names=keep_g_names,
        replacer=replacer,
        path_out=args.path_out,
        ttf_components=args.ttf_components,
        family_name=args.family_name
    )
    trial.process()
    trial.save()
