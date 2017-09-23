import bark
import collections as coll
import copy
import datetime as dt
import itertools

# parsing defaults

INTRO_GROUP_ANNEAL = 0.5 # seconds
SYLLABLE_GROUP_ANNEAL = 0.5 # seconds
INTRO_GROUP_SPLIT = 0.8 # seconds
SYLLABLE_GROUP_SPLIT = 0.8 # seconds
BOUT_ANNEAL = 0.5 # seconds
PHRASE_ANNEAL = 2.0 # seconds

# utility functions

def pairwise(iterable):
    """s -> (s0,s1), (s1,s2), (s2, s3), ...
    
    (copied from example functions in itertools module documentation"""
    a, b = itertools.tee(iterable)
    next(b, None)
    return zip(a, b)

def delta_t(first, second):
    """Time between end of first and beginning of second."""
    return (second.start - first.stop).total_seconds()

class BirdMetadata:
    """A container for data about a bird's vocalization behavior."""
    def __init__(self, name, syllables, intro_note, intro_aliases, ignore=None):
        self.name = name
        self.syllables = syllables
        self.intro_note = intro_note
        self.intro_aliases = intro_aliases
        if ignore is None:
            ignore = []
        self.ignore = ignore

    def alias(self, voc, elide_garbled=True, elide_versions=True):
        """Alias a vocalization name according to Graham's labeling scheme.
        
        A garbled vocalization (usually due to experimental limitations) is
        denoted by "[name]*".
        A specific version of a vocalization (e.g., a rare syllable variant) is
        denoted by "[name]_[number]".
        
        Args:
            voc (str): vocalization name to alias
            elide_garbled (bool): convert [name]* to [name]
            elide_versions (bool): convert [name]_[number] to [name]
        
        Returns:
            str: the aliased ("ideal") vocalization name"""
        if not voc or voc in self.ignore:
            return voc
        v = voc
        if elide_garbled and v[-1] == '*':
            v = v[:-1]
        if elide_versions and '_' in v:
            garb = False
            if '*' in v:
                garb = True
            v = v.split('_')[0]
            if garb and not elide_garbled:
                v += '*'
        if v in self.intro_aliases:
            v = self.intro_note
        return v

# primary objects of contemplation

Vocalization = coll.namedtuple('Vocalization', ['start', 'stop', 'name'])
Vocalization.__doc__ = """Lightweight container for a single vocalization."""
Vocalization.start.__doc__ = """datetime.datetime object"""
Vocalization.stop.__doc__ = """datetime.datetime object"""
Vocalization.name.__doc__ = """string"""

class VocGroup:
    """A group of vocalizations, referenced to a master vocalization list."""
    def __init__(self, voc_list, voc_idxs=None):
        self.voc_list = voc_list
        self.voc_idxs = [] if voc_idxs is None else voc_idxs
        self.vocalizations = [voc_list[i] for i in self.voc_idxs]
    
    @property
    def first(self):
        return self.vocalizations[0]
    
    @property
    def last(self):
        return self.vocalizations[-1]
    
    @property
    def start(self):
        return self.first.start
    
    @property
    def stop(self):
        return self.last.stop
    
    def __str__(self):
        return ' '.join(v.name for v in self.vocalizations)
    
    def __iter__(self):
        for voc in self.vocalizations:
            yield voc
    
    def __getitem__(self, index):
        return self.vocalizations[index]
    
    def copy(self):
        return VocGroup(self.voc_list, copy.deepcopy(self.voc_idxs))

class Bout:
    """A common subassembly of birdsong.
    
    May contain zero or one group of intro notes, and zero or more motifs."""
    def __init__(self, voc_list, intro_group, syllable_group):
        """Construct a Bout from an intro group and a syllable group.
        
        Either group may contain zero vocalizations.
        Syllables are not parsed into motifs without a call to parse_motifs.
        
        Args:
            voc_list (list of Vocalizations)
            intro_group (VocGroup)
            syllable_group (VocGroup)"""
        self.voc_list = voc_list
        self.intro_notes = intro_group.vocalizations
        self.intro_idxs = intro_group.voc_idxs
        self.syllables = syllable_group.vocalizations
        self.syll_idxs = syllable_group.voc_idxs
        self.motifs = None
        lowest_idx = min(self.intro_idxs + self.syll_idxs)
        highest_idx = max(self.intro_idxs + self.syll_idxs)
        self.intervening_idxs = [i for i in range(lowest_idx, highest_idx)
                                 if i not in (self.intro_idxs + self.syll_idxs)]
        self.intervening_vocs = [voc_list[i] for i in self.intervening_idxs]
    
    @property
    def first(self):
        if self.intro_notes:
            return self.intro_notes[0]
        else:
            return self.syllables[0]
    
    @property
    def last(self):
        if self.motifs:
            return self.syllables[-1]
        else:
            return self.intro_notes[-1]
    
    @property
    def start(self):
        return self.first.start
    
    @property
    def stop(self):
        return self.last.stop
    
    @property
    def duration(self):
        return (self.stop - self.start).total_seconds()
    
    def parse_motifs(self, seq, alias):
        self.motifs = define_motifs(self.voc_list, self.syll_idxs, seq, alias)

# main functions of the module

def collect_vocalizations(entry_list, event_ds):
    """Collects all vocalizations from a set of Bark event datasets.
    
    Assumes that event datasets contain at least "start", "stop", and "name"
    fields. No other fields are loaded into the vocalization list.
    
    If an entry in the list doesn't contain the event dataset, it is ignored.
    
    Args:
        entry_list (list of Entries): entries to search for the event_dataset
        event_ds (string): name of dataset from which to load vocalizations
    
    Returns:
        list of Vocalizations: sorted by start time"""
    vocs = []
    for e in [entry for entry in entry_list if event_ds in entry.datasets]:
        ts = e.timestamp
        vocs.extend([Vocalization(ts + dt.timedelta(seconds=r['start']),
                                  ts + dt.timedelta(seconds=r['stop']),
                                  r['name'])
                     for _,r in e.datasets[event_ds].data.iterrows()])
    return sorted(vocs, key=lambda x: x.start)

def full_parse(voc_list,
               bird_meta,
               intro_anneal=INTRO_GROUP_ANNEAL,
               song_anneal=SYLLABLE_GROUP_ANNEAL,
               intro_split=INTRO_GROUP_SPLIT,
               song_split=SYLLABLE_GROUP_SPLIT,
               bout_anneal=BOUT_ANNEAL,
               parse_motifs=True,
               phrase_anneal=PHRASE_ANNEAL):
    """Perform all parse steps on a Vocalization list.
    
    The steps are:
        1. Separately group intro notes and song syllables.
        2. Combine groups of the same type separated by a short interval.
        3. Split groups containing long silent intervals.
        4. Combine intro note and song syllable groups into bouts.
        5. Break song syllable groups in the bouts into motifs.
        6. Combine bouts separated by a short interval into phrases.
    
    To only perform some of these steps, you can either call their functions
    independently, or you can set the threshold arguments to this function to
    render the unwanted steps toothless.
    
    Args:
        voc_list (list of Vocalizations)
        bird_meta (BirdMetadata)
        intro_anneal (number): maximum interval between intro note groups to
            be annealed (units: seconds) (default: INTRO_GROUP_ANNEAL)
        song_anneal (number): maximum interval between song syllable groups
            to be annealed (units: seconds) (default: SYLLABLE_GROUP_ANNEAL)
        intro_split (number): minimum interval between intro note groups to
            be split (units: seconds) (default: INTRO_GROUP_SPLIT)
        song_split (number): minimum interval between song syllable groups to
            be split (units: seconds) (default: SYLLABLE_GROUP_SPLIT)
        bout_anneal (number): maximum interval between an intro note group and
            a song syllable group to be combined into a bout (units: seconds)
            (default: BOUT_ANNEAL)
        parse_motifs (bool): split the syllable list in a bout into motifs
        phrase_anneal (number): maximum interval between two bouts to be
            combined into a phrase (units: seconds) (default: PHRASE_ANNEAL)
    
    Returns:
        list of Phrases"""
    in_grps = group_elements(voc_list, [bird_meta.intro_note], bird_meta.alias)
    song_grps = group_elements(voc_list, bird_meta.syllables, bird_meta.alias)
    ann_ing = anneal_groups(in_grps, intro_anneal, [g.start for g in song_grps])
    ann_sg = anneal_groups(song_grps, song_anneal, [g.start for g in in_grps])
    split_ing = split_groups(ann_ing, intro_split)
    split_sg = split_groups(ann_sg, song_split)
    bouts = define_bouts(split_ing, split_sg, bout_anneal)
    if parse_motifs:
        [b.parse_motifs(bird_meta.syllables, bird_meta.alias) for b in bouts];
    phrases = define_phrases(bouts, phrase_anneal)
    return sorted(phrases, key=lambda p: p[0].start)

# steps in the parse chain

# 1. grouping consecutive vocalizations matching a given list

def group_elements(voc_list, targets, alias_fn=lambda x: x):
    """Group adjacent runs of certain vocalizations together.
    
    Args:
        voc_list (list of Vocalizations): should be sorted in time
        targets (list of strings): names of vocalizations to group together
        alias_fn (callable: str->str): function to alias nonstandard names
    
    Returns:
        list of VocGroups: input group order is preserved"""
    groups = []
    last_in_target = False
    for idx,voc in enumerate(voc_list):
        aliased = alias_fn(voc.name)
        if aliased in targets:
            if not last_in_target:
                groups.append([])
                last_in_target = True
            groups[-1].append(idx)
        else:
            last_in_target = False
    return [VocGroup(voc_list, voc_idxs) for voc_idxs in groups]

# 2. anneal groups separated by a short interval

def anneal_groups(groups, anneal_threshold, breaks=[]):
    """Combine groups if they are separated by short intervals.
    
    Args:
        groups (list of VocGroups)
        anneal_threshold (number): adjacent groups separated by intervals of
            this duration or shorter are joined together (units: seconds)
        breaks (list of datetimes): adjacent groups on either side of any of
            these datetimes are not joined, no matter how close they are
    
    Returns:
        list of VocGroups: input group order is preserved"""
    if not groups:
        return []
    annealed = [list(groups[0].voc_idxs)]
    for cg,ng in pairwise(groups):
        song_between = [1 for b in breaks if b >= cg.stop and b <= ng.start]
        if song_between or (delta_t(cg, ng) > anneal_threshold):
            annealed.append(list(ng.voc_idxs))
        else:
            annealed[-1].extend(list(ng.voc_idxs))
    return [VocGroup(groups[0].voc_list, voc_idxs) for voc_idxs in annealed]

# 3. split groups containing long silences

def split_groups(groups, split_threshold):
    """Split VocGroups if they contain long intervals between vocalizations.
    
    Args:
        groups (list of VocGroups)
        split_threshold (number): groups containing inter-vocalization intervals
            of this duration or longer are split (units: seconds)
    
    Returns:
        list of VocGroups: input group order is preserved"""
    if not groups:
        return []
    split = []
    for grp in groups:
        start = 0
        for idx,(cn,nn) in enumerate(pairwise(grp.voc_idxs)):
            if delta_t(grp.voc_list[cn], grp.voc_list[nn]) >= split_threshold:
                voc_idxs = grp.voc_idxs[start:idx + 1]
                split.append(voc_idxs)
                start = idx + 1
        final_voc_idxs = grp.voc_idxs[start:]
        split.append(final_voc_idxs)
    return [VocGroup(groups[0].voc_list, voc_idxs) for voc_idxs in split]

# 4. combine closely-spaced intro note groups & song syllable groups into bouts

def define_bouts(intro_groups, song_groups, anneal_threshold):
    """Combine closely-spaced intro note and syllable groups into Bouts.
    
    Args:
        intro_groups (list of VocGroups)
        song_groups (list of VocGroups)
        anneal_threshold (number): an intro note group and a syllable group
            separated by this interval or less are combined into a Bout
            (units: seconds)
    
    Returns:
        list of Bouts: sorted by start time"""
    sg_left = list(song_groups)
    bouts = []
    for ig in intro_groups:
        near_idx = min([i for i,g in enumerate(sg_left) if ig.stop < g.start],
                       key=lambda idx: delta_t(ig, sg_left[idx]))
        near_sg = sg_left[near_idx]
        if delta_t(ig, near_sg) <= anneal_threshold:
            bouts.append(Bout(ig.voc_list, ig, near_sg))
            sg_left.pop(near_idx);
        else:
            bouts.append(Bout(ig.voc_list, ig, VocGroup(ig.voc_list)))
    bouts.extend([Bout(g.voc_list, VocGroup(g.voc_list), g) for g in sg_left])
    return sorted(bouts, key=lambda b: b.start)

# 5. break song syllable groups into motifs

def define_motifs(voc_list, syllable_idxs, song_sequence, alias_fn):
    """Group song syllables into motifs according to song sequence.
    
    A new motif begins when the current syllable comes before the last syllable
    in the song sequence.
    
    Args:
        voc_list (list of Vocalizations): should be sorted in time
        syllable_idxs (list of ints): indexes into voc_list
        song_sequence (list of strings): names of syllables, in order
        alias_fn (callable: str->str): function to alias nonstandard names
    
    Returns:
        list of VocGroups: input order is preserved"""
    if not syllable_idxs:
        return []
    motifs = [[syllable_idxs[0]]]
    for i in syllable_idxs[1:]:
        s = voc_list[i]
        last = voc_list[motifs[-1][-1]]
        if (song_sequence.index(alias_fn(s.name)) <
            song_sequence.index(alias_fn(last.name))):
            motifs.append([i])
        else:
            motifs[-1].append(i)
    return [VocGroup(voc_list, idx_list) for idx_list in motifs]

# 6. construct phrases from closely-associated bouts

def define_phrases(bout_list, anneal_threshold):
    """Group Bouts into Phrases by proximity.
    
    Args:
        bout_list (list of Bouts): should be sorted in time
        anneal_threshold (number): maximum separation between two bouts to be
            combined into a Phrase (units: seconds)
    
    Returns:
        list of Phrases: input order is preserved"""
    if not bout_list:
        return []
    phrases = [[bout_list[0]]]
    for b in bout_list[1:]:
        if delta_t(phrases[-1][-1], b) <= anneal_threshold:
            phrases[-1].append(b)
        else:
            phrases.append([b])
    return phrases
