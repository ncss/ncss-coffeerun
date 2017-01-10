# vim: set et nosi ai ts=2 sts=2 sw=2:
# coding: utf-8

import json

COFFEE_SPECS = {}
_PRECEDENCE = ['size', 'type', 'milk', 'strength', 'iced', 'decaf', 'sugar']

_OUT_ORDER = ['size', 'iced', 'milk', 'strength', 'decaf', 'type', 'sugar']

ALLOW_TOKENS = ['with', 'please', 'i would like', 'would like', 'can i have', 'may i have', 'thanks', 'a', 'me', 'order', 'mine', 'for', 'the', 'like', 'want']


class Coffee(object):
  def __init__(self, request):
    tokens = get_all_tokens()
    self.specs = {}
    request = request.lower().strip()
    while request:
      found = False
      for token in tokens:
        if request.startswith(token):
          if token not in ALLOW_TOKENS:
            self.add_token(token)
          request = request[len(token):]
          found = True
          break
      if not found:
        space = request.find(' ')
        if space != -1:
          request = request[space:]
        else:
          return
      request = request.strip()

  def get_price_key(self, fuzzy=False):
    tokens = []
    for spec in _OUT_ORDER:
      if spec == 'type' and fuzzy:
        if self.specs[spec] in ['Cappuccino', 'Latte', 'Mocha', 'Flat White', 'Short Black', 'Long Black', 'Hot Chocolate', 'Chai Latte', 'Macchiato']:
          tokens.append('Cappuccino')
          continue
      if spec == 'size' and spec not in self.specs:
        tokens.append('Regular')
      if spec in self.specs:
        if spec == 'sugar':
          continue
        if spec == 'milk':
          # Only output the milk if it's soy
          if self.specs[spec] == 'Soy':
            tokens.append('Soy')
          continue
        tokens.append(self.specs[spec])
    return ' '.join(tokens)

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


class CoffeeSpec(object):
  def __init__(self, name, question, required=False, default=None, options=None):
    self.name = name
    self.question = question
    self.required = required
    self.default = default
    self.options = {}
    if options is None:
      options = {}
    for option in options:
      self.add_option(option, options[option])

  def add_option(self, option, alternatives):
    self.add_option_alternative(option, option)
    for alt in alternatives:
      self.add_option_alternative(option, alt)

  def add_option_alternative(self, option, alternative):
    alternative = alternative.lower()
    if option not in self.options:
      if alternative in self.options:
        raise JavaException('Duplicate name for option')
      self.options[alternative] = option

  def validate(self, value):
    if value.lower() not in self.options:
      return False
    return True

  def get_option_value(self, value):
    if not self.validate(value):
      raise JavaException('Not a valid value {} for spec {}'.format(value, self.name))
    return self.options[value.lower()]

  def get_tokens(self):
    tokens = set(self.options)
    return tokens


def get_all_tokens():
  tokens = set(ALLOW_TOKENS)

  for spec in COFFEE_SPECS:
    tokens.update(COFFEE_SPECS[spec].get_tokens())
  tokens = list(tokens)
  tokens.sort(key=(lambda x: (len(x), x)), reverse=True)
  return tokens


COFFEE_SPECS['type'] = CoffeeSpec('type', 'What type of coffee?', required=True)
COFFEE_SPECS['type'].add_option('Cappuccino', ['Cap', 'C'])
COFFEE_SPECS['type'].add_option('Latte', ['Lat', 'L'])
COFFEE_SPECS['type'].add_option('Mocha', ['M'])
COFFEE_SPECS['type'].add_option('Espresso', ['E', 'Es'])
COFFEE_SPECS['type'].add_option('Short Black', ['sb'])
COFFEE_SPECS['type'].add_option('Long Black', ['lb'])
COFFEE_SPECS['type'].add_option('Chai Latte', ['Chai'])
COFFEE_SPECS['type'].add_option('Macchiato', ['Mac', 'Macc'])
COFFEE_SPECS['type'].add_option('Flat White', ['FW'])
COFFEE_SPECS['type'].add_option('Affogato', ['Af'])
COFFEE_SPECS['type'].add_option('Hot Chocolate', ['hc', 'hot c', 'choc', 'chocolate', 'hot choc', 'hotchoc'])
COFFEE_SPECS['type'].add_option('Iced Chocolate', [])
COFFEE_SPECS['type'].add_option('Iced Coffee', [])
COFFEE_SPECS['type'].add_option('Babyccino', ['Frothaccino', 'babycino'])
COFFEE_SPECS['type'].add_option('Piccolo Latte', ['Piccolo'])
COFFEE_SPECS['type'].add_option('Tea', [])

COFFEE_SPECS['iced'] = CoffeeSpec('iced', 'Iced or normal?', required=False, options={
    'Iced': ['ice'],
    'normal': ['hot'],
})

COFFEE_SPECS['sugar'] = CoffeeSpec('sugar', 'How many sugars?', required=False, options={
    'No sugar': ['0S', '0sugar', '+0', 'no sugars'],
    '1 Sugar': ['with 1', '+1', '1S', '1sugar', 'sugar', 'sugars'],
})

for i in range(2, 12):
  i = str(i)
  COFFEE_SPECS['sugar'].add_option('{} Sugars'.format(i), ['with ' + i, i + 'S', i + 'sugar', i + ' sugar', '+' + i])

COFFEE_SPECS['decaf'] = CoffeeSpec('decaf', 'Decaf?', required=False, options={
    'Decaf': ['dec', 'lame'],
})

COFFEE_SPECS['size'] = CoffeeSpec('size', 'What size (S/L)?', required=False, options={
    'Small': ['s', 'sm'],
    'Regular': ['reg', 'r', 'rg'],
    'Large': ['L', 'lge', 'lg'],
})

COFFEE_SPECS['strength'] = CoffeeSpec('strength', 'What strength?', required=False, options={
    'Weak': ['w', 'half'],
    'Extra-shot': ['strong', 'double', 'doubleshot', 'double-shot', 'x'],
    '2 Extra-shots': ['xx', 'triple', 'tripleshot', 'triple-shot'],
    'Normal': ['standard']
})

COFFEE_SPECS['milk'] = CoffeeSpec('milk', 'What type of milk?', required=False, options={
    'Fullcream': ['normal'],
    'Skim': ['skinny', 'lite', 'light', 'sk'],
    'Soy': ['y'],
})
