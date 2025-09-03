module.exports = {
	globDirectory: 'app/',
	globPatterns: [
		'**/*.{js,css,png,json,html}'
	],
	swDest: 'app/sw.js',
	ignoreURLParametersMatching: [
		/^utm_/,
		/^fbclid$/
	]
};