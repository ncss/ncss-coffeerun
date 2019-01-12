import json
import re

COFFEE_SPECS = {}
_PRECEDENCE = ['type', 'size', 'milk', 'strength', 'iced', 'decaf', 'sugar']

CHOCOLATE_WORDS = ['chocco', 'chocie', 'choccie', 'choccy', 'chockie', 'chocky', 'choc', 'chocc']

_OUT_ORDER = ['size', 'iced', 'milk', 'strength', 'decaf', 'type', 'sugar']

# When looking at pricing, we consider the following to be all the
# same price (the price of a Cappuccino).
_CAPPUCCINO_EQUIV = {
    'Cappuccino',
    'Chai Latte',
    'Flat White',
    'Hot Chocolate',
    'Latte',
    'Long Black',
    'Macchiato',
    'Mocha',
    'Piccolo Latte',
    'Short Black',
}


class JavaException(Exception):
    pass


class Coffee(object):
    def __init__(self, request):
        request = request.lower().strip()
        # Strip punctuation except for '-' which is used in some tokens.
        # Most get replaced with space but apostrophes are just removed.
        request = re.sub('[\']', '', request)
        request = re.sub('[\'"!#$%&()*+,./:;<=>?@\\[\\]\\\\\\^_`{|}~]', ' ', request)

        request_tokens = request.split()
        request_bigrams = [' '.join(x) for x in zip(request_tokens, request_tokens[1:])]

        tokens = get_all_word_tokens()

        # Start of coffee spec gathering
        self.specs = {}

        unparsed_tokens = set(request_tokens)
        for bigram in request_bigrams:
            if bigram in tokens:
                self.add_token(bigram)
                word1, word2 = bigram.split()
                unparsed_tokens.remove(word1)
                unparsed_tokens.remove(word2)

        for request_token in set(unparsed_tokens):
            if request_token in tokens:
                self.add_token(request_token)
                unparsed_tokens.remove(request_token)

        all_abbreviation_tokens_by_spec = get_all_abbreviation_tokens_by_spec()
        for token in set(unparsed_tokens):
            result = parse_abbreviation(all_abbreviation_tokens_by_spec, token, tuple(_PRECEDENCE))
            if result:
                for spec, matched_token in result:
                    self.add_spec(spec, matched_token)
                unparsed_tokens.remove(token)

    def get_price_key(self, fuzzy_fields=None):
        if fuzzy_fields is None:
            fuzzy_fields = {}
        tokens = []
        for spec in _OUT_ORDER:
            if spec == 'type' and spec in fuzzy_fields:
                if self.specs[spec] in _CAPPUCCINO_EQUIV:
                    tokens.append('Cappuccino')
                    continue
            if spec == 'size':
                # Default to regular size if not specified.
                size = self.specs.get(spec, 'Regular')
                # If fuzzy matching, consider small and regular to be the same.
                if spec in fuzzy_fields and size == 'Small':
                    size = 'Regular'
                tokens.append(size)
                continue
            if spec == 'strength':
                strength = self.specs.get(spec, 'Normal')
                if spec in fuzzy_fields and strength == 'Weak':
                    strength = 'Normal'
                if strength != 'Normal':
                    tokens.append(strength)
                continue
            if spec in self.specs:
                if spec == 'sugar':
                    # Assume no one charges for sugar
                    continue
                if spec == 'milk':
                    # Only output the milk if it's soy
                    if self.specs[spec] in {'Soy', 'Lactose Free'}:
                        tokens.append('Soy')
                    continue
                tokens.append(self.specs[spec])
        return ' '.join(tokens)

    def get_ordered_price_keys(self):
        """Return an ordered list of pricing keys.

        The first thing in the list is the list is the most specific, then
        later items are less specific.
        """
        return [
                self.get_price_key(),
                self.get_price_key(fuzzy_fields={'type'}),
                self.get_price_key(fuzzy_fields={'type', 'size'}),
                self.get_price_key(fuzzy_fields={'type', 'size', 'strength'}),
        ]

    def add_token(self, token):
        for spec in _PRECEDENCE:
            if COFFEE_SPECS[spec].validate(token) and spec not in self.specs:
                self.add_spec(spec, token)
                return

    def add_spec(self, spec, value):
        if spec not in COFFEE_SPECS:
            raise JavaException('Unexpected spec: {}'.format(spec))
        if not COFFEE_SPECS[spec].validate(value):
            return False
        self.specs[spec] = COFFEE_SPECS[spec].get_option_value(value)
        return True

    def validation_errors(self):
        for spec in COFFEE_SPECS:
            spec = COFFEE_SPECS[spec]
            if spec.required:
                if spec.name not in self.specs:
                    yield spec

    def validate(self):
        if any(self.validation_errors()):
            return False
        return True

    def __str__(self):
        tokens = []
        for spec in _OUT_ORDER:
            if spec == 'size' and spec not in self.specs:
                tokens.append('Regular')
            if spec in self.specs:
                if spec == 'sugar':
                    tokens.append('with')
                tokens.append(self.specs[spec])
        return ' '.join(tokens)

    def toJSON(self):
        # We sort the keys to give a stable ordering in our database.
        return json.dumps(self.specs, sort_keys=True)

    @staticmethod
    def fromJSON(coffee_json):
        coffee = Coffee('C')
        coffee.specs = json.loads(coffee_json)
        if not coffee.validate():
            raise JavaException('Invalid coffee')
        return coffee


def parse_abbreviation(all_abbreviation_tokens_by_spec, token_input, remaining_specs):
    for spec in remaining_specs:
        if token_input in all_abbreviation_tokens_by_spec[spec]:
            return ((spec, token_input), )

    for spec in remaining_specs:
        for token in all_abbreviation_tokens_by_spec[spec]:
            if token_input.startswith(token):
                copy_of_remaining_specs = list(remaining_specs)
                copy_of_remaining_specs.remove(spec)
                remainder = token_input[len(token):]
                remainder_result = parse_abbreviation(all_abbreviation_tokens_by_spec, remainder, copy_of_remaining_specs)
                if remainder_result is not None:
                    return ((spec, token),) + remainder_result
    return None


class CoffeeSpecOption(object):
    def __init__(self, specname, name, abbreviations, word_tokens):
        self.specname = specname
        self.name = name
        self.word_tokens = [x.lower() for x in word_tokens]
        self.abbreviations = [x.lower() for x in abbreviations]
        if self.name.lower() not in self.word_tokens:
            self.word_tokens.append(self.name.lower())

    def __hash__(self):
        return hash(self.specname + ':' + self.name)

    def ___eq___(self, other):
        return self.specname == other.specname and self.name == other.name


class CoffeeSpec(object):
    def __init__(self, name, question, required=False, default=None, options=None):
        self.name = name
        self.question = question
        self.required = required
        self.default = default
        self.word_tokens = {}
        self.abbreviation_tokens = {}
        self.options = set()
        if options is None:
            options = []
        for option in options:
            self.add_option(option)

    def create_option(self, name, abbreviation_tokens, word_tokens):
        # 'Latte', ['l'], ['Lat']
        option = CoffeeSpecOption(self.name, name, abbreviation_tokens, word_tokens)
        self.add_option(option)

    def add_option(self, option):
        self.options.add(option)
        self.add_word_tokens(option)
        self.add_abbreviations(option)

    def add_word_tokens(self, option):
        for token in option.word_tokens:
            token = token.lower()
            if token in self.word_tokens:
                raise JavaException(f'Duplicate word token for option {option.name}.')
            self.word_tokens[token] = option

    def add_abbreviations(self, option):
        for abb in option.abbreviations:
            abb = abb.lower()
            if abb in self.abbreviation_tokens:
                raise JavaException(f'Duplicate abbreviation token {abb} for option {option.name}.')
            self.abbreviation_tokens[abb] = option

    def validate(self, value):
        value = value.lower()
        if value in self.word_tokens:
            return True
        if value in self.abbreviation_tokens:
            return True
        return False

    def get_option_value(self, value):
        value = value.lower()
        if not self.validate(value):
            raise JavaException('Not a valid value {} for spec {}'.format(value, self.name))
        if value in self.word_tokens:
            return self.word_tokens[value].name
        if value in self.abbreviation_tokens:
            return self.abbreviation_tokens[value].name

    def get_word_tokens(self):
        out = set()
        for opt in self.options:
            for word_token in opt.word_tokens:
                out.add(word_token)
        return out

    def get_abbreviation_tokens(self):
        out = set()
        for opt in self.options:
            for abb_token in opt.abbreviations:
                out.add(abb_token)
        return out


def get_all_word_tokens():
    tokens = set()
    for spec in COFFEE_SPECS:
        tokens.update(COFFEE_SPECS[spec].get_word_tokens())
    tokens = list(tokens)
    tokens.sort(key=(lambda x: (len(x), x)), reverse=True)
    return tokens


def get_all_abbreviation_tokens_by_spec():
    abbreviation_tokens_by_spec = {}
    for spec in _PRECEDENCE:
        abbreviation_tokens_by_spec[spec] = set(COFFEE_SPECS[spec].get_abbreviation_tokens())
    return abbreviation_tokens_by_spec


COFFEE_SPECS['type'] = CoffeeSpec('type', 'What type of coffee?', required=True)
COFFEE_SPECS['type'].create_option('Cappuccino', ['c', 'cap'], ['Cap', 'capp'])
COFFEE_SPECS['type'].create_option('Latte', ['l', 'lat'], ['Lat', 'lattee'])
COFFEE_SPECS['type'].create_option('Mocha', [], ['Moch'])
COFFEE_SPECS['type'].create_option('Espresso', ['Es'], [])
COFFEE_SPECS['type'].create_option('Short Black', ['sb'], [])
COFFEE_SPECS['type'].create_option('Long Black', ['lb'], [])
COFFEE_SPECS['type'].create_option('Chai Latte', [], ['Chai'])
COFFEE_SPECS['type'].create_option('Macchiato', [], ['Mac', 'Macc'])
COFFEE_SPECS['type'].create_option('Flat White', ['FW'], [])
COFFEE_SPECS['type'].create_option('Affogato', ['Af'], [])
COFFEE_SPECS['type'].create_option('Hot Chocolate', ['hc'], ['hot c', 'choc', 'chocolate'] + ['hot ' + word for word in CHOCOLATE_WORDS])
COFFEE_SPECS['type'].create_option('Iced Chocolate', [], ['iced ' + word for word in CHOCOLATE_WORDS] + ['icy ' + word for word in CHOCOLATE_WORDS] + ['icey ' + word for word in CHOCOLATE_WORDS])
COFFEE_SPECS['type'].create_option('Iced Coffee', [], [])
COFFEE_SPECS['type'].create_option('Babyccino', [], ['Frothaccino', 'babycino'])
COFFEE_SPECS['type'].create_option('Piccolo Latte', [], ['Piccolo'])
COFFEE_SPECS['type'].create_option('Cold Drip', ['cd', 'cb'], ['cold brew'])
COFFEE_SPECS['type'].create_option('Filtered', [], [])
COFFEE_SPECS['type'].create_option('Tea', [], [])

COFFEE_SPECS['iced'] = CoffeeSpec('iced', 'Iced or normal?', required=False, options={
    CoffeeSpecOption('iced', 'Iced', [], ['ice', 'icy', 'icey']),
    CoffeeSpecOption('iced', 'normal', [], ['hot'])
})

COFFEE_SPECS['sugar'] = CoffeeSpec('sugar', 'How many sugars?', required=False, options={
    CoffeeSpecOption('sugar', 'No sugar', ['0S', '+0'], ['0sugar']),
    CoffeeSpecOption('sugar', '1 Sugar', ['+1', '1', '1s'], ['with 1', '1sugar', 'sugar']),
})

for i in range(2, 12):
    i = str(i)
    COFFEE_SPECS['sugar'].create_option(
        '{} Sugars'.format(i),
        [i + 'S', '+' + i, i],
        [i + 'sugar'])

COFFEE_SPECS['decaf'] = CoffeeSpec('decaf', 'Decaf?', required=False, options={
    CoffeeSpecOption('decaf', 'Decaf', [], ['dec'])
})

COFFEE_SPECS['size'] = CoffeeSpec('size', 'What size (S/L)?', required=False, options={
    CoffeeSpecOption('size', 'Small', ['s', 'sm'], ['smol']),
    CoffeeSpecOption('size', 'Regular', ['r'], ['reg']),
    CoffeeSpecOption('size', 'Large', ['l', 'lg'], ['lge', 'lg', 'lrg']),
})

COFFEE_SPECS['strength'] = CoffeeSpec('strength', 'What strength?', required=False, options=[
    CoffeeSpecOption('strength', 'Weak', ['w'], ['half', 'half-strength']),
    CoffeeSpecOption('strength', 'Extra-shot', ['x', 'st'], ['strong', 'double', 'doubleshot', 'double-shot']),
    CoffeeSpecOption('strength', '2 Extra-shots', ['xx'], ['triple', 'tripleshot', 'triple-shot']),
    CoffeeSpecOption('strength', 'Normal', [], ['standard'])
])

COFFEE_SPECS['milk'] = CoffeeSpec('milk', 'What type of milk?', required=False, options={
    CoffeeSpecOption('milk', 'Fullcream', [], ['normal']),
    CoffeeSpecOption('milk', 'Skim', ['sk'], ['skinny', 'lite', 'light', 'sk']),
    CoffeeSpecOption('milk', 'Soy', ['y'], []),
    CoffeeSpecOption('milk', 'Lactose Free', ['lf'], []),
})
