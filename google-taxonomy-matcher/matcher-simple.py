import os
import argparse

from whoosh import writing
from whoosh.analysis import StemmingAnalyzer
from whoosh.filedb.filestore import RamStorage
from whoosh.fields import *
from whoosh.qparser import QueryParser
from whoosh.query import Variations

def load_taxonomy(language, base_category):
    taxonomy_content = open('taxonomies/taxonomy.'+language+'.txt').read()
    lines = taxonomy_content.split('\n')
    if base_category:
        filtered_lines = []
        for index, bc in enumerate(base_category):
            base_category[index] = bc.strip().lower()
        for bc in base_category:
            filtered_lines += [line for line in lines if line.strip().lower().startswith(bc.strip().lower())]
        return filtered_lines
    else:
        return lines


def index_product_info(product_dict):
    schema = Schema(path=ID(stored=True, analyzer=StemmingAnalyzer()),
                    content=TEXT(stored=True, analyzer=StemmingAnalyzer()))
    st = RamStorage()
    st.create()
    ix = st.create_index(schema)
    writer = ix.writer()
    for key in product_dict.keys():
        writer.add_document(path=key, content=product_dict[key])
    writer.commit(mergetype=writing.CLEAR)
    return ix


def match(ix, category, weights=None):
    # get the leaf of a category, e.g. only "Chairs" from Furniture > Chairs
    index, c = get_category(category)

    # adjust query
    # replace comma and ampersand with OR
    query = re.sub('[,&]', ' OR ', c)

    with ix.searcher() as searcher:
        parsed_query = QueryParser("content", schema=ix.schema, termclass=Variations).parse(query)
        results = searcher.search(parsed_query, terms=True)
        score = 0

        for r in results:
            weight = 1
            if weights:
                weight = weights[r['path']]

            score += r.score * weight

        return score


def get_category(string):
    index = -1
    name = None
    if string:
        for s in string.split(">"):
            name = s.strip()
            index += 1
    return index, name


def get_best_match(matches):
    if not matches:
        return ''
        # find most hits
    best_score = 0
    best_category = None
    for match, score in matches.items():
        if score > best_score:
            best_score = score
            best_category = match
        # if equal score: choose the category with greater detail level
        elif score == best_score:
            index, name = get_category(best_category)
            hit_index, hit_name = get_category(match)
            if hit_index > index:
                best_category = match
    return best_category


if __name__ == "__main__":

    # read command line arguments
    parser = argparse.ArgumentParser(description='Finds category based on Google\'s taxonomy in a product description')
    parser.add_argument('language', type=str, help='Taxonomy language')
    parser.add_argument('title', type=str, help='Product title')
    parser.add_argument('description', type=str, help='Product description')
    parser.add_argument('category', type=str, help='Product category info')
    parser.add_argument('base_category', metavar='bc',
                        help='The base categories of the product. Can speed up execution a lot. Example: "Furniture", "Home & Garden"',
                        nargs="*")
    args = parser.parse_args()

    # Loading taxonomy
    categories = load_taxonomy(args.language, args.base_category)

    if not categories:
        print ("Error: base category {} not found in taxonomy".format(args.base_category), file=sys.stderr)

    weights = {'title': 1, 'description': 1, 'product type': 3}
    p = {"title": args.title, "description": args.description, "product type": args.category}

    # create index of product fields
    ix = index_product_info(p)

    # find all matches
    matches = {}
    for category in categories:
        if not category:
            continue
        score = match(ix, category, weights)
        if score:
            if not matches.get(category):
                matches[category] = score
            else:
                matches[category] += score

    # select best match
    best_match = get_best_match(matches)
    print(best_match)