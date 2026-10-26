import unittest
import path_simulation as p
from unittest.mock import patch

class AffordabilityTests(unittest.TestCase):
    def test_sale_proceeds_block_over_budget_upgrade(self):
        outgoing={'player_id':1,'player':'Held','position':'FWD','price':7.9,'selling_price':7.7}
        incoming={'player_id':20,'player':'Target','position':'FWD','price':9.0}
        # Distinct clubs avoid unrelated club limits in the real replacement code.
        squad=[outgoing]+[{'player_id':i,'position':'DEF','club':str(i),'price':4} for i in range(2,16)]
        with patch.object(p,'horizon_value',side_effect=lambda rows,*_:10 if any(x['player_id']==20 for x in rows) else 0):
            self.assertEqual(p.transfer_candidates({'squad':squad,'bank':1.1},[9],[incoming],{}),[])
            moves=p.transfer_candidates({'squad':squad,'bank':1.3},[9],[incoming],{})
        self.assertEqual(len(moves),1)
        self.assertEqual(moves[0]['bank'],0)
        self.assertEqual(p.sell_price(moves[0]['in']),9)

    def test_deadline_and_coverage_required(self):
        with self.assertRaises(ValueError):
            p.with_selling_prices([{'player_id':1}],{'next_gw':8},9)
        with self.assertRaises(ValueError):
            p.with_selling_prices([{'player_id':1}],{'next_gw':9,'players':[]},9)
        self.assertEqual(p.with_selling_prices([{'player_id':1,'price':7.9}],{'next_gw':9,'players':[{'player_id':1,'selling_price':7.7}]},9)[0]['selling_price'],7.7)

if __name__=='__main__':
    unittest.main()
