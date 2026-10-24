# Hackathon

October 24, 2026

## 1 Main Sequence.

| Spectral type | $T_{\mathrm{eff}}$ (K) | $L/L_\odot$ | $M/M_\odot$ |
|:--------------|----------------------:|------------:|------------:|
| O | 32,000 to 45,000 | $5 \times 10^4$ to $7 \times 10^5$ | 19 to 60 |
| B | 10,000 to 31,000 | 60 to $4.5 \times 10^4$ | 2.7 to 18 |
| A | 7,400 to 9,700 | 8 to 40 | 1.75 to 2.2 |
| F | 6,000 to 7,200 | 1.5 to 7.2 | 1.1 to 1.6 |
| G | 5,400 to 5,900 | 0.55 to 1.35 | 0.90 to 1.06 |
| K | 3,900 to 5,300 | 0.08 to 0.46 | 0.59 to 0.88 |
| M | 2,400 to 3,900 | $3 \times 10^{-4}$ to 0.07 | 0.08 to 0.57 |

**Table 1:** Representative effective temperatures, bolometric luminosities and masses of main-sequence stars (luminosity class V), using rounded dwarf calibrations [?]. The O-star range covers O3-O9.5.

we will take logs of luminosity to get a linear scale in base 10

**Table 2: Amended Luminosity**

| Spectral type | $T_{\mathrm{eff}}$ (K) | $\log_{10}(L/L_\odot)$ | $M/M_\odot$ |
|:--------------|----------------------:|----------------------:|------------:|
| O | 32,000 to 45,000 | 4.70 to 5.85 | 19 to 60 |
| B | 10,000 to 31,000 | 1.78 to 4.65 | 2.7 to 18 |
| A | 7,400 to 9,700 | 0.90 to 1.60 | 1.75 to 2.2 |
| F | 6,000 to 7,200 | 0.18 to 0.86 | 1.1 to 1.6 |
| G | 5,400 to 5,900 | $-0.26$ to 0.13 | 0.90 to 1.06 |
| K | 3,900 to 5,300 | $-1.10$ to $-0.337$ | 0.59 to 0.88 |
| M | 2,400 to 3,900 | $-3.52$ to $-1.15$ | 0.08 to 0.57 |

**Table 3: Amended Luminosity**

To scale this to have all positive relative values, add 5 to the amended luminosities. This means that the smallest M stars have a relative value of 1.48.

$$
P = 100 \times \left(5 + \log_{10}(L/L_\odot)\right)
\tag{1}
$$

**Figure 1:** $P$ = Price of share, $L$ = luminosity $L_\odot$ = solar luminosity

The price per share will now be:

$100 \times \left(5 + \log_{10}\left(\frac{L}{L_\odot}\right)\right)$ !!

I will also suggest that each star has the same number of shares associated to it. However, if scaling by mass makes more sense, then i may suggest we change that.

For now, each star has 1000 shares attached to it.

## 2 exotics

the way i would like to add the next stages of life to the main sequence is to assign types of "Giant star" to the types of main sequence.

M,K,G, become red giants F,B beecome Blue Giants B become Red Hyper Giants O become Blue Hyper Giants

the values for our adjusted luminosities and therefore the price per share

| Stellar type | $T_{\mathrm{eff}}$ (K) | $\log_{10}(L/L_\odot)+5$ | $M_{\mathrm{init}}/M_\odot$ |
|:-------------|----------------------:|------------------------:|---------------------------:|
| Red giant | 3,000 to 5,000 | 6.00 to 9.00 | 0.8 to 8 |
| Blue giant | 10,000 to 45,000 | 7.00 to 11.00 | 3 to 70 |
| Red hypergiant | 3,000 to 4,000 | 10.00 to 10.70 | 20 to 40 |
| Blue hypergiant | 10,000 to 30,000 | 10.30 to 11.48 | 30 to 100 |

**Table 4:** Illustrative effective temperatures, shifted logarithmic bolometric luminosities and initial masses of giant and hypergiant stars. These overlapping ranges are representative rather than strict classification boundaries.

share price is of course 100 times $5 + \log_{10}(L/L_\odot)$ this stays

## 3 Proto star.

The way i would like this to work is that we will give the option to the user to "buy" into the star at the protostar stage. There will be news surrounding this in game. A protostar will have attached to it a constantly updating "predicted value" per share. The real value may very well be that value or it might deviate significantly depedning on market conditions or observational error.

## 4 Supernovae

I would like it that M,K and G type stars go from giant straight to its remnant phase, everything else will supernova.

Supernova will see a temporary $\times 3$ increase in price until a given point. after this given point in time the price should reasonably quickly decay to a value to illustrate the formation of a stellar remnant.

Type M, G, K become white dwarfs. Type F,A become neutron stars Type B and O become black holes

| Remnant type | $T_{\mathrm{eff}}$ (K) | $\log_{10}(L/L_\odot)+5$ | $M_{\mathrm{rem}}/M_\odot$ |
|:-------------|----------------------:|------------------------:|--------------------------:|
| White dwarf | 4,000 to 150,000 | 0.00 to 7.00 | 0.2 to 1.3 |
| Neutron star | $10^5$ to $3 \times 10^6$ | 0.00 to 6.00 | 1.1 to 2.3 |

**Table 5:** Illustrative surface temperatures, shifted logarithmic thermal bolometric luminosities and current masses of cooling stellar remnants. These age-dependent ranges exclude accretion-powered emission, non-thermal pulsar emission and magnetar activity.

Black holes have a Luminosity of 0 therefore their price should be 0 forever. After an initial supernova, the price should very slowly fall for about 30 seconds plus or minus 3 seconds. Then a sharp linear decrease tending towards the price of the Giants' associated remnant based on its type. This applies to all stars that experience supernova (F,A,B,O). For stars that don't (M, K, G), a reasonably slow linear decrease to the associated stellar remnant
