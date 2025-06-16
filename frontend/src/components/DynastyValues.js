import React, { useState, useEffect, useMemo } from 'react';

const DynastyValues = () => {
    const [playerValues, setPlayerValues] = useState([]);
    const [pickValues, setPickValues] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [sortConfig, setSortConfig] = useState({ key: 'value_1qb', direction: 'desc' });

    useEffect(() => {
        const fetchData = async () => {
            try {
                const playerValuesRes = await fetch('http://localhost:5001/api/dynasty_player_values');
                const pickValuesRes = await fetch('http://localhost:5001/api/dynasty_pick_values');

                if (!playerValuesRes.ok || !pickValuesRes.ok) {
                    throw new Error('Failed to fetch data');
                }

                const playerValuesData = await playerValuesRes.json();
                const pickValuesData = await pickValuesRes.json();

                setPlayerValues(playerValuesData);
                setPickValues(pickValuesData);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    const playerValuesWithPercentiles = useMemo(() => {
        if (playerValues.length === 0) return [];

        const valuesByPosition = playerValues.reduce((acc, player) => {
            const pos = player.pos;
            if (!acc[pos]) {
                acc[pos] = [];
            }
            acc[pos].push(player.value_1qb);
            return acc;
        }, {});

        return playerValues.map(player => {
            const pos = player.pos;
            const values = valuesByPosition[pos];
            const percentile = (values.filter(v => v <= player.value_1qb).length / values.length) * 100;
            return { ...player, percentile: percentile.toFixed(0) };
        });
    }, [playerValues]);

    const sortedPlayerValues = useMemo(() => {
        let sortableItems = [...playerValuesWithPercentiles];
        if (sortConfig !== null) {
            sortableItems.sort((a, b) => {
                if (a[sortConfig.key] < b[sortConfig.key]) {
                    return sortConfig.direction === 'asc' ? -1 : 1;
                }
                if (a[sortConfig.key] > b[sortConfig.key]) {
                    return sortConfig.direction === 'asc' ? 1 : -1;
                }
                return 0;
            });
        }
        return sortableItems;
    }, [playerValuesWithPercentiles, sortConfig]);

    const requestSort = (key) => {
        let direction = 'asc';
        if (sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    if (loading) {
        return <div>Loading...</div>;
    }

    if (error) {
        return <div>Error: {error}</div>;
    }

    return (
        <div>
            <h2>Dynasty Player Values</h2>
            <table>
                <thead>
                    <tr>
                        <th onClick={() => requestSort('player')}>Player</th>
                        <th onClick={() => requestSort('pos')}>Position</th>
                        <th onClick={() => requestSort('value_1qb')} title="Value in single-quarterback leagues">Value</th>
                        <th onClick={() => requestSort('percentile')}>Positional Rank</th>
                    </tr>
                </thead>
                <tbody>
                    {sortedPlayerValues.map((player, index) => (
                        <tr key={index}>
                            <td>{player.player_name || player.player || player.full_name}</td>
                            <td>{player.pos}</td>
                            <td>{player.value_1qb}</td>
                            <td>{player.percentile}%</td>
                        </tr>
                    ))}
                </tbody>
            </table>

            <h2>Dynasty Pick Values</h2>
            <table>
                <thead>
                    <tr>
                        <th>Pick</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    {pickValues.map((pick, index) => (
                        <tr key={index}>
                            <td>{pick.pick}</td>
                            <td>{pick.value_1qb}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
};

export default DynastyValues;
