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
                                intro_aliases=[],
                                ignore=['z'])

The optional parameter `ignore` allows you to specify label names which should not be included in the parse - for example, if 'z' denotes a cagemate call, including it in `ignore` will ensure that cagemate calls don't interfere with parsing. (They may not interfere even if included, but this option allows you to be certain.)

You can then obtain phrases, bouts, and motifs by running `full_parse()`.

    phrases = zfparse.full_parse(vocs, birdmeta)

The module contains some default constants for the parameters of parsing, which work reasonably well for many birds. You should examine the results of the parsing to see if you need to adjust these parameters (which you can do in the call to `full_parse()`) for your bird.

## Sample output

A call to `full_parse()` produces a list of phrases, each of which is simply a list of `Bout` objects.

    >>> phrases = full_parse(...)
    >>> phrases
    [[<Bout ...>, <Bout ...>],
     [<Bout ...>],
     [<Bout ...>, <Bout ...>, <Bout ...>]]
    >>> phrases[0]
    [<Bout ...>, <Bout ...>]

A `Bout` bundles together a sequence of zero or more introductory notes and a sequence of zero or more syllables, which are broken into motifs. A `Bout` also keeps track of intervening vocalizations, such as short calls that occur in the middle of these sequences without breaking them.

A `Bout`'s introductory notes are stored as a list of `Vocalizations`, which possess a `start` and `stop` (both `datetime` objects) and a `name`.

    >>> phrases[0][0].intro_notes
    [Vocalization(start=datetime.datetime(...), stop=datetime.datetime(...), name='i'),
     Vocalization(start=datetime.datetime(...), stop=datetime.datetime(...), name='i')]

A `Bout`'s motifs are stored as a list of `VocGroup` objects.

    >>> phrases[0][0].motifs
    [<VocGroup ...>, <VocGroup ...>]

These `VocGroup` objects contain `Vocalization` objects, which can be accessed as if the `VocGroup` were a list.

    >>> [v.name for v in phrases[0][0].motifs[0]]
    ['a', 'b', 'c', 'd', 'e']
    >>> phrases[0][0].motifs[0][3]
    Vocalization(start=datetime.datetime(...), stop=datetime.datetime(...), name='d')

### DataFrame output

The `dataframe_from_phrases()` function will construct a Pandas DataFrame from a phrase list. The columns are:

1. the phrase number within the list
2. the bout number within a phrase
3. the motif number within a bout
    * this will be 'intro' for intro notes
    * this will be 'extra' for intervening vocalizations
4. the vocalization number within a motif or 'intro' or 'extra' group
5. the vocalization start datetime
6. the vocalization stop datetime
7. the vocalization name

## Parsing explanation

[Coming soon]

