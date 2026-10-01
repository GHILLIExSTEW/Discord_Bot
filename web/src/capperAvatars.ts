const avatarObjects: Record<string, string> = {
  shot1dude: 'shot1dude-79588daf587b.webp',
  mrpod: 'mr-pod-c8d2dcf9aacb.webp',
  darkhorse: 'darkhorse-244fa3b69952.webp',
  chief: 'chief-67dd66e43f51.webp',
  capnhooks: 'capn-hooks-230822d5db12.webp',
  robin: 'r-o-b-i-n-fe8410f2675d.webp',
}

const avatarBaseUrl = 'https://lhsevzucmmzetpshpffv.supabase.co/storage/v1/object/public/website-assets/avatars/'

export function getCapperAvatarUrl(name: string): string | undefined {
  const normalizedName = name.normalize('NFKD').replace(/\p{M}/gu, '').toLowerCase().replace(/[^a-z0-9]/g, '')
  const objectName = avatarObjects[normalizedName]
  return objectName ? avatarBaseUrl + objectName : undefined
}