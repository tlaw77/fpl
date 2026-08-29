import full_squad_chip_optimizer as opt

# Production search budget: retain strong candidates plus cheap enablers, but keep
# the 30-minute ETL comfortably bounded. The core optimiser still enforces all
# roster, club and budget constraints and re-scores finalists exactly.
opt.SHORTLIST_TOP = {'GKP': 12, 'DEF': 18, 'MID': 20, 'FWD': 16}
opt.CHEAP_EXTRA = 6
opt.BEAM_WIDTH = 1600
opt.FINALISTS = 60

if __name__ == '__main__':
    opt.run()
