const sort = (rects) => rects.sort((A, B) => {
  const top = (A.pageNumber || 0) * A.top - (B.pageNumber || 0) * B.top;
  if (top === 0) {
    return A.left - B.left;
  }
  return top;
});
const overlaps = (A, B) => A.pageNumber === B.pageNumber && A.left <= B.left && B.left <= A.left + A.width;
const sameLine = (A, B, yMargin = 5) => A.pageNumber === B.pageNumber && Math.abs(A.top - B.top) < yMargin && Math.abs(A.height - B.height) < yMargin;
const inside = (A, B) => A.pageNumber === B.pageNumber && A.top > B.top && A.left > B.left && A.top + A.height < B.top + B.height && A.left + A.width < B.left + B.width;
const nextTo = (A, B, xMargin = 10) => {
  const Aright = A.left + A.width;
  const Bright = B.left + B.width;
  return A.pageNumber === B.pageNumber && A.left <= B.left && Aright <= Bright && B.left - Aright <= xMargin;
};
const extendWidth = (A, B) => {
  A.width = Math.max(B.width - A.left + B.left, A.width);
};
const optimizeClientRects = (clientRects) => {
  const rects = sort(clientRects);
  const toRemove = /* @__PURE__ */ new Set();
  const firstPass = rects.filter((rect) => {
    return rects.every((otherRect) => {
      return !inside(rect, otherRect);
    });
  });
  let passCount = 0;
  while (passCount <= 2) {
    for (const A of firstPass) {
      for (const B of firstPass) {
        if (A === B || toRemove.has(A) || toRemove.has(B)) {
          continue;
        }
        if (!sameLine(A, B)) {
          continue;
        }
        if (overlaps(A, B)) {
          extendWidth(A, B);
          A.height = Math.max(A.height, B.height);
          toRemove.add(B);
        }
        if (nextTo(A, B)) {
          extendWidth(A, B);
          toRemove.add(B);
        }
      }
    }
    passCount += 1;
  }
  return firstPass.filter((rect) => !toRemove.has(rect));
};
export {
  optimizeClientRects
};
