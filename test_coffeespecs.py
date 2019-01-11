import unittest

from coffeespecs import Coffee, get_all_word_tokens


class TestCoffeeValidation(unittest.TestCase):
    def test_minimal_spec(self):
        c = Coffee('')
        self.assertFalse(c.validate())
        self.assertTrue(c.add_spec('type', 'C'))
        self.assertTrue(c.validate())
        self.assertTrue(c.add_spec('size', 'l'))
        self.assertTrue(c.validate())

        # Still valid if we add more.
        self.assertTrue(c.add_spec('milk', 'soy'))


class TestParser(unittest.TestCase):
    def test_get_tokens(self):
        tokens = get_all_word_tokens()

        self.assertIn('chocolate', tokens)
        self.assertIn('extra-shot', tokens)
        # All tokens should be lowercase
        self.assertTrue(all([x.islower() for x in tokens]))

    def test_parse(self):
        c = Coffee('Large Cap')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                'type': 'Cappuccino',
                'size': 'Large',
        })

    def test_parse_abbreviation1(self):
        c = Coffee('LC')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                'type': 'Cappuccino',
                'size': 'Large',
        })

    def test_parse_abbreviation2(self):
        c = Coffee('SC')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                'type': 'Cappuccino',
                'size': 'Small',
        })

    def test_parse_bigram_sugars(self):
        c = Coffee('Large Cap 2 Sugars')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                'type': 'Cappuccino',
                'size': 'Large',
                'sugar': '2 Sugars',
        })

    def test_parse_words1(self):
        c = Coffee('Small strong cap')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                'type': 'Cappuccino',
                'size': 'Small',
                'strength': 'Extra-shot',
        })

    def test_parse_words2(self):
        c = Coffee('Small doubleshot cap')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                'type': 'Cappuccino',
                'size': 'Small',
                'strength': 'Extra-shot',
        })

    def test_parse_words(self):
        c = Coffee('Small Latte')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                'type': 'Latte',
                'size': 'Small',
        })

    def test_parse_abbreviation_sl(self):
        c = Coffee('SL')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                'type': 'Latte',
                'size': 'Small',
        })

    def test_parse_abbreviation_ll(self):
        c = Coffee('LL')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                'type': 'Latte',
                'size': 'Large',
        })

    def test_parse_abbreviation_cl(self):
        c = Coffee('CL')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                'type': 'Cappuccino',
                'size': 'Large',
        })

    def test_parse_abbreviation_2s(self):
        c = Coffee('CL 2S')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                'type': 'Cappuccino',
                'size': 'Large',
                'sugar': '2 Sugars',
        })

    def test_parse_words_iced(self):
        c = Coffee('Large Iced Latte')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                'type': 'Latte',
                'size': 'Large',
                'iced': 'Iced',
        })

    def test_parse_words3(self):
        c = Coffee('Large Flat white')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                'type': 'Flat White',
                'size': 'Large',
        })

    def test_parse_words_and_abbreviations_and_bigrams(self):
        c = Coffee('Large FW 3 Sugars')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                'type': 'Flat White',
                'size': 'Large',
                'sugar': '3 Sugars',
        })

    def test_parse_words4(self):
        c = Coffee('Regular Flat White')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                'type': 'Flat White',
                'size': 'Regular',
        })

    def test_parse_words_many(self):
        c = Coffee('Soy decaf latte with 2 sugars')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                'type': 'Latte',
                'sugar': '2 Sugars',
                'decaf': 'Decaf',
                'milk': 'Soy',
        })

    def test_parse_abbreviation3(self):
        c = Coffee('lffw')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                'type': 'Flat White',
                'milk': 'Lactose Free',
        })

    def test_parse_words_iced_coffee(self):
        c = Coffee('Soy Iced Coffee')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                'type': 'Iced Coffee',
                'milk': 'Soy',
        })

    def test_parse_words_iced_coffee2(self):
        c = Coffee('Skim Iced Chocolate')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                'type': 'Iced Chocolate',
                'milk': 'Skim',
        })

    def test_parse_words_lactose_free(self):
        c = Coffee('Lactose Free Cap')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                    'type': 'Cappuccino',
                    'milk': 'Lactose Free',
        })

    def test_parse_abbreviation4(self):
        c = Coffee('lfw')
        self.assertTrue(c.validate())
        self.assertEqual(c.specs, {
                    'type': 'Flat White',
                    'size': 'Large',
        })

    def test_abbreviation_parsing(self):
        self.assertEqual(str(Coffee('yfw')), 'Regular Soy Flat White')
        self.assertEqual(str(Coffee('lyc')), 'Large Soy Cappuccino')
        self.assertEqual(str(Coffee('yhc')), 'Regular Soy Hot Chocolate')
        self.assertEqual(str(Coffee('syc')), 'Small Soy Cappuccino')
        self.assertEqual(str(Coffee('syfw')), 'Small Soy Flat White')
        self.assertEqual(str(Coffee('skl')), 'Regular Skim Latte')
        self.assertEqual(str(Coffee('xskl')), 'Regular Skim Extra-shot Latte')
        self.assertEqual(str(Coffee('sk fw')), 'Regular Skim Flat White')
        self.assertEqual(str(Coffee('stl')), 'Regular Extra-shot Latte')
        self.assertEqual(str(Coffee('shc')), 'Small Hot Chocolate')
        self.assertEqual(str(Coffee('lhc')), 'Large Hot Chocolate')


class TestWeirdCoffeeInput(unittest.TestCase):
    def test_joel(self):
        c = Coffee('It is a truth universally acknowledged, that a single joel in possession of a good fortune, must be in want of an extra-shot piccolo latte in the morning, plox.')
        self.assertEqual(c.specs, {
            'type': 'Piccolo Latte',
            'strength': 'Extra-shot',
        })
        self.assertTrue(c.validate())

    def test_liam(self):
        c = Coffee('let\'s try this again. I would very much enjoy if you could provide me with an Iced latte please thank you for listening to my TED Talk')
        self.assertEqual(c.specs, {
                'type': 'Latte',
                'iced': 'Iced',
        })
        self.assertTrue(c.validate())

    def test_shelley(self):
        c = Coffee('gimme the flat white bean pls')
        self.assertEqual(c.specs, {
                'type': 'Flat White',
        })
        self.assertTrue(c.validate())

    def test_shelley2(self):
        c = Coffee('yo beanie boy give me a smol iced latte pls')
        self.assertEqual(c.specs, {
                'size': 'Small',
                'iced': 'Iced',
                'type': 'Latte',
        })
        self.assertTrue(c.validate())

    def test_shelley3(self):
        c = Coffee('my best boy hit me with an iced latte pls')
        self.assertEqual(c.specs, {
            'iced': 'Iced',
            'type': 'Latte'
        })

    def test_jackson(self):
        c = Coffee('bestow upon me thy chocolated fount in the morrow, i\'m ploxed to request this of you')
        self.assertFalse(c.validate())


class TestPrettyPrint(unittest.TestCase):

    def test_print_large_cap(self):
        c = Coffee('Large Cap')
        self.assertEqual('Large Cappuccino', str(c))

    def test_print_small_cap(self):
        c = Coffee('SC')
        self.assertEqual('Small Cappuccino', str(c))

    def test_print_large_cap2(self):
        c = Coffee('Large Cap 2 Sugars')
        self.assertEqual('Large Cappuccino with 2 Sugars', str(c))

    def test_print_small_strong_cap(self):
        c = Coffee('Small strong cap')
        self.assertEqual('Small Extra-shot Cappuccino', str(c))

    def test_print_small_latte(self):
        c = Coffee('Small Latte')
        self.assertEqual('Small Latte', str(c))

    def test_print_reg_latte(self):
        c = Coffee('Reg L')
        self.assertEqual('Regular Latte', str(c))

    def test_print_large_latte(self):
        c = Coffee('LL')
        self.assertEqual('Large Latte', str(c))

    def test_print_large_iced_latte(self):
        c = Coffee('Large Iced Latte')
        self.assertEqual('Large Iced Latte', str(c))

    def test_print_large_flat_white(self):
        c = Coffee('Large Flat white')
        self.assertEqual('Large Flat White', str(c))

    def test_print_large_flat_white_3s(self):
        c = Coffee('Large FW 3 Sugars')
        self.assertEqual('Large Flat White with 3 Sugars', str(c))

    def test_print_regular_flat_white(self):
        c = Coffee('Regular Flat White')
        self.assertEqual('Regular Flat White', str(c))

    def test_print_soy_decaf_latte_2s(self):
        c = Coffee('Soy decaf latte with 2 sugars')
        self.assertEqual('Regular Soy Decaf Latte with 2 Sugars', str(c))


if __name__ == '__main__':
    unittest.main()
