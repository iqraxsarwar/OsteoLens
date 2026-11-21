import test from 'node:test'
import assert from 'node:assert/strict'
import en from './locales/en/common.json' with {type:'json'}
import tr from './locales/tr/common.json' with {type:'json'}
test('English and Turkish contain matching messages and interpolation variables',()=>{
  assert.deepEqual(Object.keys(en).sort(),Object.keys(tr).sort())
  for(const [key,value] of Object.entries(en)) {
    assert.ok(tr[key].trim(),key)
    assert.deepEqual((value.match(/\{\{[^}]+\}\}/g)||[]).sort(),(tr[key].match(/\{\{[^}]+\}\}/g)||[]).sort(),key)
  }
})
