import json
import collections
import statistics
import queue

CategorySpec = collections.namedtuple('CategorySpec', 'name reverse')
with open('languages.json', 'r') as my_file:
    data = json.load(my_file)
    for _, json_object in data.items():
        json_object['languages'] = [s.replace('-', ' ').strip().lower() for s in json_object['languages']]

def langs_for_cats(languages, categories):
    results = {}
    for num_of_langs in range(1, len(languages)):
        for cutoff in range(10):
            cats = set(categories)
            lang_cats = []
            last_cat_len = 0
            while cats and last_cat_len != len(cats):
                last_cat_len = len(cats)
                best_lang = None 
                cats_for_lang = set()
                max_score = 0
                for lang in languages:
                    ranks = get_ranks(lang, cats, available_langs=languages)
                    current_cats = [cat for cat, rank in ranks.items() if rank <= cutoff]
                    score = len(current_cats)
                    if score > max_score:
                        best_lang = lang
                        cats_for_lang = set(current_cats)
                        max_score = score
                if best_lang:
                    lang_cats.append((best_lang, tuple(cats_for_lang)))
                    cats -= set(cats_for_lang)
            if not cats:
                key = tuple(lang_cats)
                if key not in results or cutoff < results[key]:
                    results[key] = cutoff
    return results

def _category_filter(filter_test, categories=None):
    categories = categories or [cat for cat in data]
    return sorted([cat for cat in categories if filter_test(cat)])

def cat_starts_with(*strings, categories=None, invert=False):
    filter_test = lambda cat: invert != any(s for s in strings if cat.startswith(s))
    return _category_filter(filter_test, categories)

def cat_includes(*strings, categories=None, invert=False):
    filter_test = lambda cat: invert != any(s for s in strings if s in cat)
    return _category_filter(filter_test, categories)

def get_ranks(language, categories, available_langs=None):
    language = language.strip().lower()
    ranks = {}
    cat_langs = {cat: data[cat]['languages'] for cat in categories}
    for cat, langs in cat_langs.items():
        if available_langs:
            langs = [l for l in langs if l in available_langs]
        for index, lang in enumerate(langs):
            if lang == language:
                ranks[cat] = index
                break
    return ranks

def filter_good_langs(languages, rank, categories, available_langs=None):
    """
    rank: 0-based index. For example, if rank==4, only categories in which the language is ranked >= 5 will be included in the result.
    """
    for lang in languages:
        ranks = get_ranks(lang, categories, available_langs=available_langs)
        categories = [c for c in categories if c not in ranks or ranks[c] > rank]
    return categories

def lang_best_ranks(language):
    all_cats = all_categories()
    ranks = get_ranks(language, all_cats)
    ranks = [(k, v) for k, v in ranks.items()]
    return sorted(ranks, key=lambda kv: kv[1])

def get_category(string, quiet=True):
    cats = [cat for cat in data if string in cat]
    number_found = len(cats)
    selected_cat = None
    if number_found == 0:
        print("Nothing found")
        return None
    index = 0
    if number_found > 1:
        print("Multiple matches. Please choose one.")
        print()
        for index, cat in enumerate(cats):
            print(index, cat)
        print()
        index = int(input("Enter a number.\n"))
    selected_cat = cats[index]
    if not quiet:
        print()
        print(f"selected category: {selected_cat}")
    languages = data[selected_cat]['languages']
    if not quiet:
        for i, lang in enumerate(languages):
            print(i, lang)
    return languages

def compare(cats=None, quiet=False):
    categories = []
    if cats:
        for cat in cats:
            answer = None
            invert = False
            while not answer:
                answer = input(f"Invert category '{cat}'?\n").strip().lower()
                print()
                if answer and answer[0] == 'y':
                    invert = True
            categories.append((cat, invert))
    else:
        search_string = None
        while True:
            if not search_string:
                search_string = input("Enter search text. Type 'done' to stop.\n")
                print()
                if not search_string:
                    search_string = None
                    print("Bad value. Try again.")
                    continue
                if search_string.strip().lower() == 'done':
                    break
            values = cat_includes(search_string)
            if not values:
                search_string = None
                print("Search string yielded no results. Try Again.")
                continue
            if len(values) > 10:
                search_string = None
                print("Too many values. Be more specific.")
                continue
            indices = [0]
            if len(values) > 1:
                print("Got these values:")
                for i, val in enumerate(values):
                    print(f"{i}: {val}")
                print()
                xxx = "To choose categories enter their index numbers separated by commas.\n"
                yyy = "You can also enter a range, e.g. 2..5 \n"
                input_val = input(f"{xxx}{yyy}")
                print()
                index_range = False
                if '..' in input_val:
                    index_range = True
                    indices = input_val.split('..')
                    try:
                        indices = [int(i.strip()) for i in indices]
                        indices = list(range(indices[0], indices[1] + 1))
                    except ValueError:
                        search_string = None
                        print("Bad index. Search Again.")
                        continue
                else:
                    indices = input_val.split(',')
                    try:
                        indices = [int(i.strip()) for i in indices]
                    except ValueError:
                        search_string = None
                        print("Bad index. Search Again.")
                        continue
            try:
                values_to_use = [v for i, v in enumerate(values) if i in indices]
            except IndexError:
                search_string = None
                print("Bad index. Search Again.")
                continue
            invert_none = False
            for value_to_use in values_to_use:
                if invert_none:
                    categories.append((value_to_use, False))
                    continue
                answer = None
                invert = False
                while not answer:
                    answer = input(f"Invert category '{value_to_use}'?\n").strip()
                    print()
                    if answer:
                        if answer.lower()[0] == 'y':
                            invert = True
                        elif answer[0] == 'N':
                            invert_none = True
                categories.append((value_to_use, invert))
            search_string = None
    if categories:
        category_specs = [CategorySpec(category, invert) for category, invert in categories]
        lang_list = compute_scores(category_specs)
        if not quiet:
            print("Categories:")
            for category, invert in categories:
                print(f"{category} {'(INVERTED)' if invert else ''}")
            print()
            print("Languages:")
            for l in lang_list:
                print(l)
            print()
        return lang_list
    return []


def compute_scores(category_specs):
    category_specs = list(category_specs)
    langs = collections.defaultdict(int)
    # with open('languages.json', 'r') as my_file:
    #     data = json.load(my_file)
    for category_name, json_obj in data.items():
        categories = [c for c in category_specs if c.name in category_name.strip().lower()]
        if not any(categories):
            continue
        assert len(categories) == 1
        category = categories[0]
        lang_list = json_obj['languages']
        list_len = 52
        for i, lang in enumerate(lang_list):
            val = list_len - i
            if category.reverse:
                val = i + 1
            langs[lang] += val

    lang_list = [(l, v) for l, v in langs.items()]
    list_avg = statistics.mean(x[1] for x in lang_list)
    list_stdev = statistics.pstdev(x[1] for x in lang_list)
    lang_list = [(l[0], round((l[1]-list_avg)/list_stdev, 2)) for l in lang_list]
    lang_list = [l for l in lang_list if l[0] != 'none']
    lang_list = sorted(lang_list, key=lambda l: l[1], reverse=True)
    return lang_list


def declare_global_variables():
    def pc():
        would_use = cat_starts_with('i would use')
        good_for = cat_includes('good for')
        good_for = cat_includes('beginner', 'children', categories=good_for, invert=True)
        excels = cat_includes('excels')
        suitable = cat_includes('suitable for real')
        results = would_use + good_for + excels + suitable
        return [x for x in results if not any(y for y in ['beginner', 'children', 'symbolic'] if y in x)]

    global all_cats
    all_cats = [cat for cat in data]
    global github
    github = data['github repo rankings']['languages']
    global open_source
    open_source = get_category('open source', quiet=True)
    global corporate_languages
    corporate_languages = ['csharp', 'fsharp', 'visual basic', 'objective c', 'swift']
    global practical_categories
    practical_categories = pc()
    global minimal
    minimal = get_category('minimal', quiet=True)
    global large
    large = get_category('this language is large', quiet=True)
    global small
    small = [x for x in minimal[:18] if x in large[-18:]] 
    global smart_enough
    smart_enough = get_category('smart', quiet=True)
    global glance
    glance = get_category('glance', quiet=True)
    global accidental_compexity
    accidental_compexity = get_category('complexity', quiet=True)
    global semantics
    semantics = get_category('semantics', quiet=True)
    global tacked_on
    tacked_on = get_category('tacked on', quiet=True)
    global shoot_yourself
    shoot_yourself = get_category('shoot yourself', quiet=True)
    global readable
    readable = get_category('readable')
    global looks_like
    looks_like = get_category('looks like')
    global improved
    improved = get_category('improve', quiet=True)
    global influence
    influence = get_category('influence', quiet=True)
    global static_type
    static_type = get_category('static', quiet=True)
    global lisps
    lisps = set(['scheme', 'elisp', 'emacs lisp', 'clojure', 'common lisp'])
    global ml_langs
    ml_langs = set(['standard ml', 'ocaml', 'fsharp', 'haskell', 'scala', 'coq', 'agda'])
    # global hard_cats
    # hard_cats = ['minimal', 'language is large', 'smart enough', 'glance', 'accidental complexity', 'semantics', 'tacked on', 'shoot yourself', 'readable', 'looks like']
    # hard_cats = {s: cat_includes(s)[0] for s in hard_cats}
    # global hard_lang_lists
    # hard_lang_lists = {cat: get_category(cat) for s, cat in hard_cats.items()}
    global hard_langs
    hard_langs = set(['c++', 'common lisp', 'scala', 'haskell', 'ocaml', 'fsharp'])

 

declare_global_variables()
