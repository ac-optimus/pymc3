#   Copyright 2020 The PyMC Developers
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
"""
Sphinx plugin to run generate a gallery for notebooks

Modified from the seaborn project, which modified the mpld3 project.
"""
import base64
import json
import os
import glob
import shutil
import runpy

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from matplotlib import image

DOC_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_IMG_LOC = os.path.join(
            os.path.dirname(DOC_SRC), "logos", "PyMC3.png"
        )
TABLE_OF_CONTENTS_FILENAME = "table_of_contents_{}.js"

INDEX_TEMPLATE = """
.. _{sphinx_tag}:

.. title:: {gallery}_notebooks

.. raw:: html

    <h1 class="ui header">{Gallery} Notebooks</h1>
    <div id="gallery" class="ui vertical segment">
    </div>
"""


def create_thumbnail(infile, width=275, height=275, cx=0.5, cy=0.5, border=4):
    """Overwrites `infile` with a new file of the given size"""
    im = image.imread(infile)
    rows, cols = im.shape[:2]
    size = min(rows, cols)
    if size == cols:
        xslice = slice(0, size)
        ymin = min(max(0, int(cx * rows - size // 2)), rows - size)
        yslice = slice(ymin, ymin + size)
    else:
        yslice = slice(0, size)
        xmin = min(max(0, int(cx * cols - size // 2)), cols - size)
        xslice = slice(xmin, xmin + size)
    thumb = im[yslice, xslice]
    thumb[:border, :, :3] = thumb[-border:, :, :3] = 0
    thumb[:, :border, :3] = thumb[:, -border:, :3] = 0

    dpi = 100
    fig = plt.figure(figsize=(width / dpi, height / dpi), dpi=dpi)

    ax = fig.add_axes([0, 0, 1, 1], aspect="auto", frameon=False, xticks=[], yticks=[])
    ax.imshow(thumb, aspect="auto", resample=True, interpolation="bilinear")
    fig.savefig(infile, dpi=dpi)
    plt.close(fig)
    return fig


class NotebookGenerator:
    """Tools for generating an example page from a file"""

    def __init__(self, filename, target_dir):
        self.basename = os.path.basename(filename)
        self.stripped_name = os.path.splitext(self.basename)[0]
        self.output_html = os.path.join(
            "..", "notebooks", "{}.html".format(self.stripped_name)
        )
        self.image_dir = os.path.join(target_dir, "_images")
        self.png_path = os.path.join(
            self.image_dir, "{}.png".format(self.stripped_name)
        )
        with open(filename, "r") as fid:
            self.json_source = json.load(fid)
        self.pagetitle = self.extract_title()
        self.default_image_loc = DEFAULT_IMG_LOC

        # Only actually run it if the output RST file doesn't
        # exist or it was modified less recently than the example
        if not os.path.exists(self.output_html) or (
            os.path.getmtime(self.output_html) < os.path.getmtime(filename)
        ):

            self.gen_previews()
        else:
            print("skipping {0}".format(filename))

    def extract_preview_pic(self):
        """By default, just uses the last image in the notebook."""
        pic = None
        for cell in self.json_source["cells"]:
            for output in cell.get("outputs", []):
                if "image/png" in output.get("data", []):
                    pic = output["data"]["image/png"]
        if pic is not None:
            return base64.b64decode(pic)
        return None

    def extract_title(self):
        for cell in self.json_source["cells"]:
            if cell["cell_type"] == "markdown":
                rows = [row.strip() for row in cell["source"] if row.strip()]
                for row in rows:
                    if row.startswith("# "):
                        return row[2:]
        return self.basename.replace("_", " ")

    def gen_previews(self):
        preview = self.extract_preview_pic()
        if preview is not None:
            with open(self.png_path, "wb") as buff:
                buff.write(preview)
        else:
            shutil.copy(self.default_image_loc, self.png_path)
        create_thumbnail(self.png_path)


class TableOfContentsJS:
    """Container to load table of contents JS file"""

    def load(self, path):
        """Creates an attribute ``contents`` by running the JS file as a python
        file.

        """
        runpy.run_path(path, {"Gallery": self})


def build_gallery(srcdir, gallery):
    working_dir = os.getcwd()
    os.chdir(srcdir)
    static_dir = os.path.join(srcdir, "_static")
    target_dir = os.path.join(srcdir, "nb_{}".format(gallery))
    image_dir = os.path.join(target_dir, "_images")
    source_dir = os.path.abspath(
        os.path.join(os.path.dirname(os.path.dirname(srcdir)), "notebooks")
    )
    table_of_contents_file = os.path.join(
        source_dir, TABLE_OF_CONTENTS_FILENAME.format(gallery))
    tocjs = TableOfContentsJS()
    tocjs.load(table_of_contents_file)

    if not os.path.exists(static_dir):
        os.makedirs(static_dir)

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    if not os.path.exists(image_dir):
        os.makedirs(image_dir)

    if not os.path.exists(source_dir):
        os.makedirs(source_dir)
    
    # Create default image
    default_png_path = os.path.join(os.path.join(target_dir, "_images"), "default.png")
    shutil.copy(DEFAULT_IMG_LOC, default_png_path)
    create_thumbnail(default_png_path)

    # Write individual example files
    data = {}
    for basename in sorted(tocjs.contents):
        if basename.find(".rst") < 1:
            filename = os.path.join(source_dir, basename + ".ipynb")
            ex = NotebookGenerator(filename, target_dir)
            data[ex.stripped_name] = {
                "title": ex.pagetitle,
                "url": os.path.join(os.sep, gallery, ex.output_html),
                "thumb": os.path.basename(ex.png_path),
            }
        else:
            filename = basename.split(".")[0]
            data[basename] = {
                "title": " ".join(filename.split("_")),
                "url": os.path.join(os.sep, gallery, "../"+filename+".html"),
                "thumb": os.path.basename(default_png_path),
            }

    js_file = os.path.join(image_dir, "gallery_{}_contents.js".format(gallery))
    with open(table_of_contents_file, "r") as toc:
        table_of_contents = toc.read()

    js_contents = "Gallery.examples = {}\n{}".format(
        json.dumps(data), table_of_contents
    )

    with open(js_file, "w") as js:
        js.write(js_contents)

    with open(os.path.join(target_dir, "index.rst"), "w") as index:
        index.write(INDEX_TEMPLATE.format(
            sphinx_tag="notebook_gallery",
            gallery=gallery,
            Gallery=gallery.title().rstrip("s")
        ))

    os.chdir(working_dir)


def main(app):
    for gallery in ("tutorials", "examples"):
        build_gallery(app.builder.srcdir, gallery)


def setup(app):
    app.connect("builder-inited", main)
