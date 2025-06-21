import React, { useState, useEffect, useMemo } from 'react';

const DynastyValues = () => {
    const [playerData, setPlayerData] = useState([]);
    const [pickValues, setPickValues] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [sortConfig, setSortConfig] = useState({ key: 'ecr', direction: 'asc' }); // Default sort by ECR ascending

    useEffect(() => {
        const fetchData = async () => {
            try {
                // Fetch combined player data which now includes ECR
                const allPlayersRes = await fetch('http://localhost:5001/api/all_player_names_with_data');
                const pickValuesRes = await fetch('http://localhost:5001/api/dynasty_pick_values');

                if (!allPlayersRes.ok || !pickValuesRes.ok) {
                    throw new Error('Failed to fetch data');
                }

                const allPlayersData = await allPlayersRes.json();
                const pickValuesData = await pickValuesRes.json();

                setPlayerData(allPlayersData);
                setPickValues(pickValuesData);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    const sortedPlayerData = useMemo(() => {
        let sortableItems = [...playerData];
        if (sortConfig !== null) {
            sortableItems.sort((a, b) => {
                const aValue = typeof a[sortConfig.key] === 'string' ? a[sortConfig.key].toLowerCase() : a[sortConfig.key];
                const bValue = typeof b[sortConfig.key] === 'string' ? b[sortConfig.key].toLowerCase() : b[sortConfig.key];

                // Handle potential 'N/A' or null values for numeric sorts
                const isNumeric = ['ecr', 'sd', 'best', 'worst', 'rank_delta'].includes(sortConfig.key);
                if (isNumeric) {
                    const numA = aValue === 'n/a' || aValue === null ? Infinity : Number(aValue);
                    const numB = bValue === 'n/a' || bValue === null ? Infinity : Number(bValue);
                    if (numA < numB) {
                        return sortConfig.direction === 'asc' ? -1 : 1;
                    }
                    if (numA > numB) {
                        return sortConfig.direction === 'asc' ? 1 : -1;
                    }
                } else {
                    if (aValue < bValue) {
                        return sortConfig.direction === 'asc' ? -1 : 1;
                    }
                    if (aValue > bValue) {
                        return sortConfig.direction === 'asc' ? 1 : -1;
                    }
                }
                return 0;
            });
        }
        return sortableItems;
    }, [playerData, sortConfig]);

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
            <h2>Dynasty Player ECR Data</h2>
            <table>
                <thead>
                    <tr>
                        <th onClick={() => requestSort('name')}>Player</th>
                        <th onClick={() => requestSort('position')}>Position</th>
                        <th onClick={() => requestSort('team')}>Team</th>
                        <th onClick={() => requestSort('ecr')}>ECR</th>
                        <th onClick={() => requestSort('sd')}>SD</th>
                        <th onClick={() => requestSort('best')}>Best</th>
                        <th onClick={() => requestSort('worst')}>Worst</th>
                        <th onClick={() => requestSort('rank_delta')}>Rank Delta</th>
                        <th onClick={() => requestSort('bye_week')}>Bye</th>
                    </tr>
                </thead>
                <tbody>
                    {sortedPlayerData.map((player, index) => (
                        <tr key={index}>
                            <td>{player.name}</td>
                            <td>{player.position}</td>
                            <td>{player.team}</td>
                            <td>{player.ecr ? player.ecr.toFixed(1) : 'N/A'}</td>
                            <td>{player.sd ? player.sd.toFixed(2) : 'N/A'}</td>
                            <td>{player.best || 'N/A'}</td>
                            <td>{player.worst || 'N/A'}</td>
                            <td>{player.rank_delta ? player.rank_delta.toFixed(1) : 'N/A'}</td>
                            <td>{player.bye_week || 'N/A'}</td>
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
