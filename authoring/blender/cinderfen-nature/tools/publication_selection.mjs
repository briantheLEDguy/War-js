import crypto from 'node:crypto';

/** An explicit selection never broadens to unreviewed siblings. */
export function publicationSelection(knownIds, argument) {
  const ids = argument === undefined ? [...knownIds] : argument.split(',');
  if (!ids.length || ids.some(id => !knownIds.includes(id)) || new Set(ids).size !== ids.length) throw Error('Unknown, empty or duplicate nature asset selection.');
  ids.sort();
  const suffix = argument === undefined ? '' : '-' + crypto.createHash('sha256').update(ids.join('\n')).digest('hex').slice(0, 12);
  return { ids, scoped: argument !== undefined, build: suffix ? `review/build${suffix}.json` : 'build-report.json',
    review: `review/review${suffix}.json`, validation: suffix ? `review/validation${suffix}.json` : 'validation.json' };
}

export function verifySelectionReview(review, selection, buildHash, images) {
  if (review.approved !== true || !review.reviewedBy || !review.reviewedAt || Number.isNaN(Date.parse(review.reviewedAt))) throw Error('Named, dated internal visual acceptance is required.');
  if (review.buildSha256 !== buildHash) throw Error('Review belongs to a different build.');
  if (selection.scoped && JSON.stringify(review.assetIds) !== JSON.stringify(selection.ids)) throw Error('Visual receipt must name exactly the selected assets.');
  for (const [name, digest] of Object.entries(images)) if (review.images?.[name] !== digest) throw Error('Unreviewed actual-export image: ' + name);
}
