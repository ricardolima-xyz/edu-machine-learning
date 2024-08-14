import os
import argparse
import logging

import pandas as pd
from pandas.core.series import Series
from whoosh import writing
from yaml import load, Loader
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
        #writer.add_document(path=unicode(key, "utf-8"), content=unicode(product_dict[key], "utf-8"))
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
        if results:
            logging.debug("Category: %s => Query: %s" % (category, query))
        for r in results:
            weight = 1
            if weights:
                weight = weights[r['path']]

            logging.debug("Result: %s [score: %d weight: %d]" % (r, r.score, weight))
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


def safe_get(row, column):
    value = row.get(column)
    if isinstance(value, str):
        return value
    return ''


if __name__ == "__main__":

    # read command line arguments
    parser = argparse.ArgumentParser(description='Finds category based on Google\'s taxonomy in a product description')
    parser.add_argument('language', type=str, help='Taxonomy language')
    parser.add_argument('title', type=str, help='Product title')
    parser.add_argument('description', type=str, help='Product description')
    parser.add_argument('category', type=str, help='Product category info')

    # TODO CONSIDER CLEANUP
    parser.add_argument('base_category', metavar='bc',
                        help='The base categories of the product. Can speed up execution a lot. Example: "Furniture", "Home & Garden"',
                        nargs="*")
    parser.add_argument('-o', '--overwrite', const=True, nargs="?",
                        help='If set category column in product file will be overwritten')
    parser.add_argument('--log', nargs="?", help="The log level")
    args = parser.parse_args()

    # TODO REMOVE
    print(args)

    # logging
    if args.log:
        logging.basicConfig(level=args.log.upper())

    # load settings
    settings = {}
    if os.path.exists("settings.yaml"):
        settings = load(open("settings.yaml"), Loader=Loader)
    product_file = settings.get("product_file", "product.csv")
    output_product_file = settings.get("output_product_file", "product.matched.csv")
    product_columns = settings.get("product_columns", ["title", "product type", "description"])
    product_column_weights = settings.get("product_column_weights", [3, 2, 1])
    weights = {}
    for index, pc in enumerate(product_columns):
        weights[pc] = product_column_weights[index]

    google_category_column = settings.get("google_category_column", "google product category")
    if args.overwrite:
        overwrite_category = True
    else:
        overwrite_category = settings.get("overwrite_category", False)

    # Loading taxonomy
    print ("Loading taxonomy. Base categories: {} ...".format(", ".join(args.base_category)))
    categories = load_taxonomy(args.language, args.base_category)

    if not categories:
        print ("Error: base category {} not found in taxonomy".format(args.base_category))

    if not args.base_category:
        print ("Warning: you did not specify a base category. This can take *very* long time to complete. See matcher -h for help.")

    # load product csv file
    print ("Parsing input file: {}".format(product_file))
    product_data = pd.read_csv(product_file, sep='\t', usecols=product_columns + [google_category_column])
    print ("Processing {} rows ...".format(product_data.shape[0]))

    # if target google category column doesnt exist in file: add
    if not google_category_column in product_data.columns:
        product_data[google_category_column] = Series()

    # iterate through data row by row and match category
    index = 1
    replacements = 0
    for row_index, row in product_data.iterrows():
        index += 1
        if index % 10 == 0:
            print ("Progress: {} rows finished".format(index))
        p = {}
        for col in product_columns:
            value = safe_get(row, col)
            if value:
                p[col] = row.get(col)
        gcat = safe_get(row, google_category_column)

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

        logging.debug("MATCHES: %s" % str(matches))
        logging.debug("======> best match: %s" % best_match)

        if not gcat or overwrite_category:
            if best_match:
                product_data.loc[index - 2, google_category_column] = best_match
                #row[google_category_column] = best_match
                replacements += 1

    # write back result
    # copy category column into original file
    gcat_col = product_data[google_category_column]

    original_data = pd.read_csv(product_file, sep='\t')
    original_data[google_category_column] = gcat_col
    original_data.to_csv(output_product_file, sep='\t', index=False)
    print ("processed {} rows of '{}', replaced {},  output written to '{}'".format(
        (index - 1), product_file, replacements, output_product_file))



