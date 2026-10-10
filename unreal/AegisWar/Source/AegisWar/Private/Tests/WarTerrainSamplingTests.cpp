#if WITH_DEV_AUTOMATION_TESTS
#include "Misc/AutomationTest.h"
#include "WarInterfaceCatalog.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FWarTerrainSamplingTest,"AegisWar.Foundation.TerrainSamplingBounds",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FWarTerrainSamplingTest::RunTest(const FString& Parameters)
{
    TSharedPtr<FJsonObject> Root;
    const FString Json=TEXT(R"({"campaign":{"zones":[{"id":"a"},{"id":"b"},{"id":"c"},{"id":"d"},{"id":"e"}]},"maps":[{"id":"a","definition":{"size":32,"spatial":{"bounds":{"minX":-3600,"maxX":3600,"minZ":-3400,"maxZ":3400},"terrainBounds":{"minX":-12,"maxX":20,"minZ":-8,"maxZ":16},"playableOutline":[{"x":-10,"z":-6},{"x":18,"z":-6},{"x":18,"z":5},{"x":3,"z":5},{"x":3,"z":14},{"x":-10,"z":14}]}}},{"id":"b","definition":{"size":32,"spatial":{"bounds":{"minX":-12,"maxX":20,"minZ":-8,"maxZ":16}}}},{"id":"c","definition":{"size":100,"spatial":{"bounds":{"minX":-100,"maxX":100,"minZ":-100,"maxZ":100},"terrainBounds":{"minX":-101,"maxX":100,"minZ":-100,"maxZ":100}}}},{"id":"d","definition":{"size":100,"spatial":{"bounds":{"minX":-100,"maxX":100,"minZ":-100,"maxZ":100},"terrainBounds":{"minX":-10,"maxX":10,"minZ":-10,"maxZ":10},"playableOutline":[{"x":30,"z":0},{"x":0,"z":0},{"x":0,"z":5}]}}},{"id":"e","definition":{"size":100}}]})");
    TestTrue(TEXT("Sampling fixture parses"),FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Root));
    const auto Catalog=FWarInterfaceCatalog::Parse(Root);
    const auto* Expanded=Catalog.FindZone(TEXT("a"));
    TestNotNull(TEXT("Expanded zone admitted"),Expanded);
    if (Expanded)
    {
        TestEqual(TEXT("Distant content ownership retained"),Expanded->ContentBounds.Min,FVector2D(-3600,-3400));
        TestEqual(TEXT("Atlas samples local minimum with source Z inversion"),Expanded->TerrainBounds.Min,FVector2D(-12,-16));
        TestEqual(TEXT("Atlas samples local maximum with source Z inversion"),Expanded->TerrainBounds.Max,FVector2D(20,8));
        TestEqual(TEXT("Concave outline retained"),Expanded->PlayableOutline.Num(),6);
    }
    for (const TCHAR* Id:{TEXT("b"),TEXT("c"),TEXT("d"),TEXT("e")})
    {
        const auto* Zone=Catalog.FindZone(Id);
        TestNotNull(TEXT("Fallback zone admitted"),Zone);
        if (Zone)
        {
            TestEqual(TEXT("Legacy or invalid sampling falls back to content minimum"),Zone->TerrainBounds.Min,Zone->ContentBounds.Min);
            TestEqual(TEXT("Legacy or invalid sampling falls back to content maximum"),Zone->TerrainBounds.Max,Zone->ContentBounds.Max);
        }
    }
    return true;
}
#endif
