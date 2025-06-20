""" Tom Aubier 2025 """

import re, hashlib, copy, pathlib, argparse
import deepl

hashed_token_dict = {}

def get_deepl_api_key():
    is_api_valid = False
    is_api_key_loaded_from_file = False
    deepl_api_key_fpath = pathlib.Path.home() / '.latex_translator_deepl_api_key.txt'
    while not is_api_valid:

        if deepl_api_key_fpath.exists():
            with open(deepl_api_key_fpath, 'r', encoding='utf-8') as f:
                auth_key = f.read()
            is_api_key_loaded_from_file = True
        else:
            auth_key = input('Please provide a DeepL API key under the format xxx-xxx-xxx-xxx-xxx:fx\n')
        
        # check api key validity
        try:
            dummy_translator = deepl.Translator(auth_key)
            dummy_result = dummy_translator.translate_text(
                'bla', source_lang='FR', target_lang="EN-GB",
            )
            dummy_result.text

            # save if valid
            if not is_api_key_loaded_from_file:
                with open(deepl_api_key_fpath, 'w', encoding='utf-8') as f:
                    f.write(auth_key)
                print(f'DeepL API key saved in {deepl_api_key_fpath}')
            else:
                print(f'DeepL API key loaded from {deepl_api_key_fpath}')

            is_api_valid = True
        except Exception as e:
            is_api_key_loaded_from_file = False
            print(f'The API key appears to be invalid: {type(e).__name__}:\n{str(e)}')
    return auth_key

def get_str_token_hash(str_token):
    hash_object = hashlib.sha256()
    obj_bytes = str(str_token).encode('utf-8')
    hash_object.update(obj_bytes)
    hash_value = hash_object.hexdigest()[:8]
    hash_tag = f'<{hash_value}>'
    return hash_tag

def get_hashed_latex_text(latex_text):
    global hashed_token_dict
    hashed_text = copy.deepcopy(latex_text)

    for regex_pattern in latex_token_regex_search_patterns:
        if not isinstance(regex_pattern, tuple):
            regex_pattern = (regex_pattern, re.MULTILINE) # (pattern, findall option) -> MULTILINE by default
        extracted_tokens = re.findall(regex_pattern[0], latex_text, regex_pattern[1])

        for extracted_token in extracted_tokens:
            if isinstance(extracted_token, str):
                token_hash = get_str_token_hash(extracted_token)
                hashed_token_dict[token_hash] = extracted_token
                hashed_text = hashed_text.replace(extracted_token, token_hash)
            else:
                raise TypeError('Unsupported extracted token type')
    return hashed_text

def populate_hashed_tokens(translated_text):
    translated_text = rf"{translated_text}"
    for hashed_citation_tag, citation_str in hashed_token_dict.items():
        translated_text = translated_text.replace(hashed_citation_tag, rf"{citation_str}")
    return translated_text

def translate_hashed_text(hashed_text, target_lang, source_lang=None):
    deepl_result = translator.translate_text(
        hashed_text,
        source_lang=source_lang,
        target_lang=target_lang,
        preserve_formatting=True,
        ignore_tags=hashed_token_dict.keys()
    )
    return deepl_result.text

# %% --- filtered expressions ---

latex_token_regex_search_patterns = [ # order matters
    
    # --- latex environments ---

    *[
        (r'(\\begin\{' + env_type + r'\}.*?\\end\{' + env_type + r'\})', re.DOTALL)
        for env_type in [
            r'equation\*',
            r'equation',
            r'figure\*',
            r'figure',
            r'align',
            r'strip',
            r'table',
            r'table\*',
        ]
    ],

    # --- equations ---

    r'\$.*?\$',      # $...$
    r'\$\$.*?\$\$',  # $$...$$
    r'\\\[.*?\\\]',  # \[...\]

    # --- misc ---

    r'^\s*%.*', # latex comments (find lines starting with optional whitespace followed by %)
    r'\\(?:cite|footnotecite)\{.*?\}', # cite / footnotecite commands
]

# --- main ---

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--input_file_path', '-i', dest='input_file_path', type=str, default=None, help='Specify the path of the .tex file to be translated')
    parser.add_argument('--target_lang', '-t', dest='target_lang', type=str, default=None, help='Language of the document to be translated (eg. FR, EN-GB, ES, etc.)')
    parser.add_argument('--source_lang', dest='source_lang', type=str, default=None, help='Language of the document to be translated (optional, Deepl will detect it if not provided)')
    parser.add_argument('--output_debug_file', dest='output_debug_file', type=bool, default=False, help='Output hashed token text file (for debug)')

    args = parser.parse_args()

    # Init deepl API
    auth_key = get_deepl_api_key()
    translator = deepl.Translator(auth_key)

    # Load source
    input_fpath = pathlib.Path(args.input_file_path)
    with open(input_fpath, 'r', encoding='utf-8') as f:
        latex_content = f.read()

    # hash latex tokens to be preserved
    hashed_text = get_hashed_latex_text(latex_content)

    if args.output_debug_file:
        from datetime import datetime
        current_time = datetime.now().strftime("> Time of execution: %H:%M:%S\n\n")
        debug_output_fpath = input_fpath.parent / f'{input_fpath.stem}_hashed_tokens_debug.tex'
        with open(debug_output_fpath, 'w', encoding='utf-8') as f:
            f.write(current_time + hashed_text + "\n\n--- tokens dict ---\n\n" + hashed_token_dict.__str__())
        print(f'> DEBUG hashed LaTeX written to: {debug_output_fpath}')

    else: # Skip translation when debugging

        # translation
        translated_hashed_text = translate_hashed_text(
            hashed_text, args.target_lang, args.source_lang,
        )

        # place latex token back in the translated text
        translated_latex = populate_hashed_tokens(translated_hashed_text)

        # save translated doc
        output_fpath = input_fpath.parent / f'{input_fpath.stem}_translated.tex'
        with open(output_fpath, 'w', encoding='utf-8') as f:
            f.write(translated_latex)

        print(f'> Translated LaTeX written to: {output_fpath}')


