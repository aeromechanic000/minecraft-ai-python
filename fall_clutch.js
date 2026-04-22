/**
 * Water bucket clutch — runs entirely in JS on physicsTick (~50ms).
 *
 * This is a function expression evaluated by vm.runInThisContext().
 * Called with (bot, logFn, Vec3) from cerebellum.py.
 *
 * Strategy:
 *   1. Pre-equip water bucket as soon as falling starts (async equip)
 *   2. When close to ground: look down + placeBlock with explicit face (sync packet)
 */

function(bot, logFn, Vec3) {
    var NON_SOLID = new Set([
        'air','cave_air','void_air',
        'water','flowing_water','lava','flowing_lava',
        'grass','tall_grass','fern','large_fern',
        'seagrass','tall_seagrass','kelp','kelp_plant',
        'dead_bush','dandelion','poppy','blue_orchid','allium',
        'azure_bluet','red_tulip','orange_tulip','white_tulip',
        'pink_tulip','oxeye_daisy','cornflower','lily_of_the_valley',
        'wither_rose','sunflower','rose_bush','lilac','peony',
        'torch','wall_torch','soul_torch','soul_wall_torch',
        'oak_sign','spruce_sign','birch_sign','jungle_sign',
        'acacia_sign','dark_oak_sign','mangrove_sign','cherry_sign',
        'bamboo_sign','crimson_sign','warped_sign',
        'sugar_cane','vine','lily_pad','snow',
        'wheat','carrots','potatoes','beetroots',
        'oak_sapling','spruce_sapling','birch_sapling',
        'jungle_sapling','acacia_sapling','dark_oak_sapling',
        'nether_wart','warped_fungus','crimson_fungus',
        'redstone_wire','tripwire',
    ]);

    var SAFE_LAND = new Set([
        'water','flowing_water','slime_block','hay_block',
        'cobweb','powder_snow','honey_block',
    ]);

    var UP = new Vec3(0, 1, 0);
    var st = { falling:false, done:false, y0:null, picked:false, equipped:false };

    function log(msg) { try { logFn(msg); } catch(e) {} }

    function findItem(name) {
        var items = bot.inventory.items();
        for (var i = 0; i < items.length; i++)
            if (items[i] && items[i].name === name) return items[i];
        return null;
    }

    function findItemInHotbar(name) {
        for (var slot = 36; slot <= 44; slot++) {
            var item = bot.inventory.slots[slot];
            if (item && item.name === name) return slot - 36;
        }
        return -1;
    }

    function findGround() {
        var pos = bot.entity.position;
        var x = Math.floor(pos.x), z = Math.floor(pos.z), sy = Math.floor(pos.y);
        for (var y = sy - 1; y > Math.max(sy - 40, -64); y--) {
            try {
                var b = bot.blockAt(new Vec3(x, y, z));
                if (b && !NON_SOLID.has(b.name)) return b;
            } catch(e) {}
        }
        return null;
    }

    function preEquip() {
        var nether = bot.game && bot.game.dimension && bot.game.dimension.indexOf('nether') >= 0;
        var bucketName = nether ? 'powder_snow_bucket' : 'water_bucket';
        var bucket = findItem(bucketName);
        if (!bucket && nether) bucket = findItem('water_bucket');
        if (bucket) {
            bot.equip(bucket, 'hand', function(err) {
                if (!err) {
                    st.equipped = true;
                    log('[Clutch] Pre-equipped ' + bucketName);
                }
            });
        }
    }

    function performClutch(ground) {
        var nether = bot.game && bot.game.dimension && bot.game.dimension.indexOf('nether') >= 0;
        var bucketName = 'water_bucket';
        var hotbarSlot = -1;

        if (nether) {
            hotbarSlot = findItemInHotbar('powder_snow_bucket');
            if (hotbarSlot >= 0) bucketName = 'powder_snow_bucket';
            else hotbarSlot = findItemInHotbar('water_bucket');
        } else {
            hotbarSlot = findItemInHotbar('water_bucket');
        }

        var bucket = findItem(bucketName);
        if (!bucket && nether) { bucket = findItem('water_bucket'); bucketName = 'water_bucket'; }
        if (!bucket) { log('[Clutch] No water bucket!'); return; }

        try {
            // 1. Look straight down (force=true = instant, sends look packet immediately)
            bot.look(bot.entity.yaw, Math.PI / 2, true);

            // 2. Make sure bucket is in hand
            var held = bot.heldItem;
            if (!held || held.name !== bucketName) {
                if (hotbarSlot >= 0) {
                    bot.setQuickBarSlot(hotbarSlot);
                } else {
                    log('[Clutch] Bucket not in hotbar!');
                    return;
                }
            }

            // 3. Place water — use placeBlock with explicit top-face vector.
            //    activateBlock() defers the packet via lookAt() callback (too slow).
            //    placeBlock() with an explicit face sends the packet immediately.
            bot.placeBlock(ground, UP);
            log('[Clutch] Water placed! Used: ' + bucketName);
        } catch(e) {
            log('[Clutch] placeBlock error: ' + e);
            // Fallback: try activateBlock
            try {
                bot.activateBlock(ground);
                log('[Clutch] activateBlock fallback');
            } catch(e2) {
                log('[Clutch] All methods failed: ' + e2);
            }
        }
    }

    function pickup() {
        var eb = findItem('bucket');
        if (!eb) return;
        try {
            bot.look(bot.entity.yaw, Math.PI / 2, true);
            var hotbarSlot = findItemInHotbar('bucket');
            if (hotbarSlot >= 0) {
                bot.setQuickBarSlot(hotbarSlot);
                var p = bot.entity.position;
                var bl = bot.blockAt(new Vec3(Math.floor(p.x), Math.floor(p.y)-1, Math.floor(p.z)));
                if (bl && (bl.name === 'water' || bl.name === 'flowing_water')) {
                    bot.activateBlock(bl);
                    log('[Clutch] Water picked up');
                }
            } else {
                bot.equip(eb, 'hand', function(err) {
                    if (err) return;
                    var p = bot.entity.position;
                    var bl = bot.blockAt(new Vec3(Math.floor(p.x), Math.floor(p.y)-1, Math.floor(p.z)));
                    if (bl && (bl.name === 'water' || bl.name === 'flowing_water')) {
                        bot.activateBlock(bl);
                        log('[Clutch] Water picked up');
                    }
                });
            }
        } catch(e) {}
    }

    bot.on('physicsTick', function() {
        if (!bot.entity) return;
        var v = bot.entity.velocity;
        if (!v) return;
        var vy = v.y;
        var onG = bot.entity.onGround;

        if (onG) {
            if (st.done && !st.picked) { pickup(); st.picked = true; }
            st.falling = false; st.done = false; st.y0 = null;
            st.picked = false; st.equipped = false;
            return;
        }
        if (vy >= -0.5) return;

        if (!st.falling) {
            st.falling = true; st.y0 = bot.entity.position.y;
            st.done = false; st.picked = false; st.equipped = false;
            preEquip();
        }
        if (st.done) return;

        if (bot.game && bot.game.gameMode === 'creative') return;

        try {
            var fb = bot.blockAt(bot.entity.position);
            if (fb && (fb.name==='water'||fb.name==='flowing_water'||fb.name==='ladder'||fb.name==='vine'||fb.name==='scaffolding')) return;
        } catch(e) {}

        var g = findGround();
        if (!g) return;

        var cy = bot.entity.position.y;
        var gy = g.position.y + 1;
        var dg = cy - gy;
        var fd = (st.y0 || cy) - gy;
        if (fd <= 3) return;

        try {
            var lb = bot.blockAt(g.position.offset(0, 1, 0));
            if (lb && SAFE_LAND.has(lb.name)) return;
        } catch(e) {}

        // Trigger earlier (5-8 blocks) to give server time to process water placement
        var td = Math.max(5, Math.min(8, Math.abs(vy) * 3));
        if (dg <= td) {
            log('[Clutch] Fall detected! Fall: ' + fd.toFixed(1) + ', Dist: ' + dg.toFixed(1) + ', Vel: ' + vy.toFixed(2));
            performClutch(g);
            st.done = true;
        }
    });
}
