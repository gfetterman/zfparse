# zfparse

zfparse layers structure, including motifs, bouts, and phrases, onto a sequence of zebra finch vocalizations.

## Installation

zfparse was written for Python 3.5. Installation with [Conda](http://conda.pydata.org/miniconda.html) is recommended.

    git clone https://github.com/gfetterman/zfparse
    cd zfparse
    pip install .

The zfparse data-loading function assumes your data is in [Bark](http://github.com/margoliashlab/bark) format, but the parsing itself does not. If your data is not in Bark, writing a custom data-loading routine should not be difficult.

## Usage

If your data is Bark-formatted, `collect_vocalizations()` will produce a list of vocalizations to feed into the parsing functions.

    root = bark.read_root('path/to/root')
    entries = [root.entries[e] for e in root.entries]
    vocs = zfparse.collect_vocalizations(entries, 'voc_labels.csv')

Information about a given bird's vocalization behavior is stored in a `BirdMetadata` object for simplicity.

    birdmeta = zfparse.BirdMeta(name='[birdname]',
                                syllables=['a', 'b', 'c', 'd', 'e'],
                                intro_note='i',
                                intro_aliases=[])

You can then obtain phrases, bouts, and motifs by running `full_parse()`.

    phrases = zfparse.full_parse(vocs, birdmeta)

The module contains some default constants for the parameters of parsing, which work reasonably well for many birds. You should examine the results of the parsing to see if you need to adjust these parameters (which you can do in the call to `full_parse()`) for your bird.

## Parsing explanation

[Coming soon]

